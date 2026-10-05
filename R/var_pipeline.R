# Shared VAR/AR estimation functions. No file writes or model execution on import.

lag_design <- function(values, p) {
  values <- as.matrix(values)
  n <- nrow(values); k <- ncol(values)
  stopifnot(p >= 0L, n > p, !is.null(colnames(values)))
  idx <- seq.int(p + 1L, n)
  x <- matrix(1, length(idx), 1, dimnames = list(NULL, "const"))
  if (p > 0L) for (j in seq_len(p)) {
    z <- values[idx - j, , drop = FALSE]
    colnames(z) <- paste0(colnames(values), ".l", j)
    x <- cbind(x, z)
  }
  list(x = x, y = values[idx, , drop = FALSE], row = idx)
}

ols_system <- function(design, keep = rep(TRUE, nrow(design$x))) {
  keep <- keep & complete.cases(design$x, design$y)
  x <- design$x[keep, , drop = FALSE]; y <- design$y[keep, , drop = FALSE]
  if (nrow(x) <= ncol(x) + 2L) stop("Insufficient complete training rows")
  fit <- lm.fit(x, y)
  if (fit$rank != ncol(x)) stop("Rank-deficient regression")
  b <- matrix(fit$coefficients, nrow = ncol(x), ncol = ncol(y),
              dimnames = list(colnames(x), colnames(y)))
  e <- matrix(fit$residuals, nrow = nrow(y), ncol = ncol(y), dimnames = list(NULL, colnames(y)))
  list(coefficients = b, residuals = e, n = nrow(x), k = ncol(y), predictors = ncol(x), keep = keep)
}

root_modulus <- function(coefficients, p) {
  if (p == 0L) return(0)
  k <- ncol(coefficients)
  top <- t(coefficients[-1, , drop = FALSE])
  companion <- if (p == 1L) top else rbind(top, cbind(diag(k * (p - 1L)), matrix(0, k * (p - 1L), k)))
  max(Mod(eigen(companion, only.values = TRUE)$values))
}

select_orders <- function(values, max_lag = 20L, ar = FALSE) {
  values <- as.matrix(values)
  if (ar) values <- values[, "ES", drop = FALSE]
  common <- lag_design(values, max_lag)
  common_rows <- common$row[complete.cases(common$x, common$y)]
  if (length(common_rows) < 10L * (ncol(values) * max_lag + 1L))
    warning("Lag search has relatively few complete rows for the maximum model size")
  orders <- if (ar) 0:max_lag else seq_len(max_lag)
  table <- do.call(rbind, lapply(orders, function(p) {
    d <- lag_design(values, p)
    f <- ols_system(d, d$row %in% common_rows)
    covariance <- crossprod(f$residuals) / f$n
    ld <- as.numeric(determinant(covariance, logarithm = TRUE)$modulus)
    parameters <- f$k * f$predictors
    data.frame(p = p, observations = f$n, parameters = parameters,
               AIC = ld + 2 * parameters / f$n,
               BIC = ld + log(f$n) * parameters / f$n)
  }))
  list(bic = table$p[which.min(table$BIC)], aic = table$p[which.min(table$AIC)], table = table)
}

model_specs <- function(training, max_lag) {
  levels <- select_orders(training, max_lag)
  differences <- select_orders(apply(training, 2, diff), max_lag)
  ar <- select_orders(training, max_lag, ar = TRUE)
  specs <- data.frame(
    model = c("AR_selected", "AR_match_BIC", "VAR_BIC", "AR_match_AIC", "VAR_AIC",
              "AR_diff_BIC", "VAR_diff_BIC", "AR_diff_AIC", "VAR_diff_AIC", "Persistence"),
    kind = c("AR", "AR", "VAR", "AR", "VAR", "AR", "VAR", "AR", "VAR", "Naive"),
    p = c(ar$bic, levels$bic, levels$bic, levels$aic, levels$aic,
          differences$bic, differences$bic, differences$aic, differences$aic, 0L),
    difference = c(rep(FALSE, 5), rep(TRUE, 4), FALSE), stringsAsFactors = FALSE)
  list(specs = specs, selection = rbind(transform(levels$table, search = "VAR_levels"),
                                       transform(differences$table, search = "VAR_differences"),
                                       transform(ar$table, search = "AR_levels")))
}

one_forecast <- function(history, dates, spec, suspect_dates = as.Date(character()), mask_span = 21L) {
  history <- as.matrix(history)
  last <- tail(history[, "ES"], 1)
  out <- list(predicted_log = last, predicted_variance = exp(last), smearing = 1,
              root = NA_real_, stable = NA, fitted_rows = 0L, omitted_rows = 0L,
              parameters = 0L, status = "ok", detail = "")
  if (spec$kind == "Naive") return(out)
  tryCatch({
    values <- if (spec$difference) apply(history, 2, diff) else history
    values <- as.matrix(values)
    value_dates <- if (spec$difference) dates[-1] else dates
    mask <- lag_design(values, spec$p)
    # AR and matching VAR use identical historical outcome/input availability.
    keep <- complete.cases(mask$x, mask$y)
    if (spec$model == "AR_selected") {
      own <- lag_design(values[, "ES", drop = FALSE], spec$p)
      keep <- complete.cases(own$x, own$y)
    }
    if (length(suspect_dates)) {
      issue <- dates %in% suspect_dates
      exposed <- vapply(seq_along(dates), function(i) any(issue[max(1L, i - mask_span + 1L):i]), logical(1))
      keep <- keep & !exposed[match(value_dates[mask$row], dates)]
    }
    selected <- if (spec$kind == "AR") values[, "ES", drop = FALSE] else values
    if (length(spec$subset_symbols) && !is.na(spec$subset_symbols) && nzchar(spec$subset_symbols))
      selected <- values[, strsplit(spec$subset_symbols, "/", fixed = TRUE)[[1]], drop = FALSE]
    d <- lag_design(selected, spec$p)
    f <- ols_system(d, keep)
    out$fitted_rows <- f$n
    out$omitted_rows <- nrow(d$x) - f$n
    out$parameters <- f$k * f$predictors
    out$root <- root_modulus(f$coefficients, spec$p)
    out$stable <- out$root < 1
    if (!out$stable) stop("Unstable fitted dynamics")
    xnew <- 1
    if (spec$p > 0L) xnew <- c(1, as.vector(t(tail(selected, spec$p)[spec$p:1L, , drop = FALSE])))
    if (any(!is.finite(xnew))) stop("Required origin predictors unavailable")
    predicted <- as.numeric(xnew %*% f$coefficients[, "ES"])
    if (spec$difference) predicted <- last + predicted
    smear <- mean(exp(f$residuals[, "ES"]))
    variance <- exp(predicted) * smear
    if (!is.finite(predicted) || !is.finite(variance) || variance <= 0) stop("Invalid forecast/back-transformation")
    out$predicted_log <- predicted; out$predicted_variance <- variance; out$smearing <- smear
    out
  }, error = function(e) {
    out$status <- "fallback_persistence"; out$detail <- conditionMessage(e); out
  })
}

forecast_sequence <- function(logs, dates, specs, training_end, suspect_dates = as.Date(character()), mask_span = 21L) {
  targets <- which(dates > training_end)
  records <- vector("list", length(targets) * nrow(specs)); q <- 1L
  for (i in targets) {
    history <- logs[seq_len(i - 1L), , drop = FALSE]
    for (j in seq_len(nrow(specs))) {
      spec <- specs[j, ]
      value <- one_forecast(history, dates[seq_len(i - 1L)], spec, suspect_dates, mask_span)
      records[[q]] <- data.frame(date = dates[i], origin_date = dates[i - 1L], training_end = dates[i - 1L],
                                 model = spec$model, p = spec$p, difference = spec$difference,
                                 actual_log = logs[i, "ES"], actual_variance = exp(logs[i, "ES"]),
                                 history_rows = i - 1L, value, stringsAsFactors = FALSE)
      q <- q + 1L
    }
    if ((i - targets[1] + 1L) %% 200L == 0L) message("  Completed ", i - targets[1] + 1L, " targets")
  }
  do.call(rbind, records)
}

score_forecasts <- function(forecasts) {
  do.call(rbind, lapply(split(forecasts, forecasts$model), function(f) {
    error <- f$actual_log - f$predicted_log
    ratio <- f$actual_variance / f$predicted_variance
    data.frame(model = f$model[1], observations = nrow(f), fallbacks = sum(f$status != "ok"),
               log_MSE = mean(error^2), log_RMSE = sqrt(mean(error^2)), log_MAE = mean(abs(error)),
               variance_MSE = mean((f$actual_variance - f$predicted_variance)^2),
               QLIKE = mean(ratio - log(ratio) - 1))
  }))
}

compare_pairs <- function(forecasts) {
  pairs <- list(c("AR_match_BIC", "VAR_BIC"), c("AR_match_AIC", "VAR_AIC"),
                c("AR_diff_BIC", "VAR_diff_BIC"), c("AR_diff_AIC", "VAR_diff_AIC"))
  if ("VAR_base_match_BIC" %in% forecasts$model) pairs <- c(pairs,
    list(c("VAR_base_match_BIC", "VAR_BIC"), c("VAR_base_match_AIC", "VAR_AIC")))
  losses <- list(); comparisons <- list()
  for (j in seq_along(pairs)) {
    a <- forecasts[forecasts$model == pairs[[j]][1], ]
    v <- forecasts[forecasts$model == pairs[[j]][2], ]
    stopifnot(identical(a$date, v$date), identical(a$actual_log, v$actual_log))
    ea <- a$actual_log - a$predicted_log; ev <- v$actual_log - v$predicted_log
    adjusted <- ea^2 - ev^2 + (a$predicted_log - v$predicted_log)^2
    eligible <- all(a$status == "ok" & v$status == "ok")
    stat <- p <- NA_real_
    if (eligible) {
      fit <- lm(adjusted ~ 1)
      se <- sqrt(sandwich::NeweyWest(fit, prewhite = FALSE, adjust = TRUE)[1, 1])
      stat <- mean(adjusted) / se; p <- pnorm(stat, lower.tail = FALSE)
    }
    comparisons[[j]] <- data.frame(AR = pairs[[j]][1], VAR = pairs[[j]][2],
       observations = nrow(a), gain_pct = 100 * (1 - mean(ev^2) / mean(ea^2)),
       mean_adjusted_difference = mean(adjusted), CW_statistic = stat, p_one_sided = p,
       inference_status = if (eligible) "exploratory_CW" else "withheld_due_to_fallbacks")
    losses[[j]] <- data.frame(date = a$date, AR = pairs[[j]][1], VAR = pairs[[j]][2],
                              raw_loss_difference = ea^2 - ev^2, CW_adjusted_difference = adjusted)
  }
  list(comparisons = do.call(rbind, comparisons), losses = do.call(rbind, losses))
}

initial_diagnostics <- function(training, dates, specs, output) {
  # The main grid is complete. Standard tests refer to successive common rows.
  summaries <- list(); joint <- list(); stationarity <- list()
  for (symbol in colnames(training)) {
    a <- urca::ur.df(training[, symbol], type = "drift", lags = 20, selectlags = "BIC")
    k <- urca::ur.kpss(training[, symbol], type = "mu", lags = "long")
    stationarity[[symbol]] <- data.frame(symbol = symbol, ADF_tau2 = a@teststat[1],
        ADF_critical_5pct = a@cval[1, "5pct"], KPSS = k@teststat,
        KPSS_critical_5pct = k@cval[1, "5pct"], conclusion = "Assess both tests; disagreement does not identify a structural break")
  }
  pdf(file.path(output, "training_diagnostics.pdf"), width = 11, height = 8)
  on.exit(dev.off(), add = TRUE)
  par(mfrow = c(3, 1))
  for (symbol in colnames(training)) plot(dates, training[, symbol], type = "l", main = paste(symbol, "training log variance"), xlab = "Provider date", ylab = "log variance")
  for (symbol in colnames(training)) acf(training[, symbol], lag.max = 100, main = paste(symbol, "training ACF"))
  for (j in seq_len(nrow(specs))) {
    spec <- specs[j, ]; if (spec$kind != "VAR") next
    values <- if (spec$difference) apply(training, 2, diff) else training
    fit <- vars::VAR(values, p = spec$p, type = "const")
    serial <- vars::serial.test(fit, lags.pt = 30, type = "PT.adjusted")$serial
    arch <- vars::arch.test(fit, lags.multi = 5, multivariate.only = TRUE)$arch.mul
    summaries[[spec$model]] <- data.frame(model = spec$model, p = spec$p,
        observations = fit$obs, parameters = length(coef(fit$varresult$ES)) * ncol(values),
        max_root = max(vars::roots(fit)),
        serial_p = pchisq(as.numeric(serial$statistic), as.numeric(serial$parameter), lower.tail = FALSE),
        ARCH_p = pchisq(as.numeric(arch$statistic), as.numeric(arch$parameter), lower.tail = FALSE))
    residual <- residuals(fit)
    par(mfrow = c(3, 3))
    for (symbol in colnames(residual)) {
      plot(residual[, symbol], type = "l", main = paste(spec$model, symbol), xlab = "Common-row index", ylab = "Residual")
      acf(residual[, symbol], main = paste(symbol, "residual ACF"))
      acf(residual[, symbol]^2, main = paste(symbol, "squared residual ACF"))
    }
    par(mfrow = c(2, 2))
    ccf(residual[, "ES"], residual[, "CL"], main = paste(spec$model, "ES/CL residual CCF"))
    ccf(residual[, "ES"], residual[, "GC"], main = paste(spec$model, "ES/GC residual CCF"))
    qqnorm(residual[, "ES"], main = paste(spec$model, "ES residual QQ")); qqline(residual[, "ES"])
    hist(residual[, "ES"], breaks = 50, main = paste(spec$model, "ES residuals"), xlab = "Residual")
    # vars alters the stored terms' intercept flag; rebuild the identical OLS
    # equation so sandwich's score and bread matrices have matching dimensions.
    equation_data <- data.frame(ES_target = fit$datamat[, "ES"], fit$datamat[, -(1:ncol(values)), drop = FALSE])
    equation <- lm(ES_target ~ . - 1, data = equation_data)
    stopifnot(isTRUE(all.equal(unname(coef(equation)), unname(coef(fit$varresult$ES)), tolerance = 1e-10)))
    covariance <- sandwich::NeweyWest(equation, prewhite = FALSE, adjust = TRUE)
    for (markets in list("CL", "GC", c("CL", "GC"))) {
      positions <- which(vapply(names(coef(equation)), function(s) any(startsWith(s, paste0(markets, ".l"))), logical(1)))
      b <- coef(equation)[positions]; v <- covariance[positions, positions, drop = FALSE]
      w <- as.numeric(t(b) %*% solve(v, b))
      joint[[length(joint) + 1L]] <- data.frame(model = spec$model, markets = paste(markets, collapse = "+"),
        null = "All indicated market lags are zero in ES equation", restrictions = length(b),
        Wald_HAC = w, p_asymptotic = pchisq(w, length(b), lower.tail = FALSE),
        caveat = "Training association; HAC asymptotic test; no identified economic causality")
    }
  }
  list(diagnostics = do.call(rbind, summaries), stationarity = do.call(rbind, stationarity),
       joint = do.call(rbind, joint))
}
