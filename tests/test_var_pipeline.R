# Run: Rscript --vanilla tests/test_var_pipeline.R
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])
root <- dirname(dirname(normalizePath(script)))
source(file.path(root, "R", "var_pipeline.R"))
set.seed(140)
values <- matrix(rnorm(900, -8, .7), ncol = 3, dimnames = list(NULL, c("ES", "CL", "GC")))
dates <- as.Date("2020-01-01") + seq_len(nrow(values)) - 1L
spec <- data.frame(model = "VAR_BIC", kind = "VAR", p = 3L, difference = FALSE)
custom <- one_forecast(values, dates, spec)
native <- vars::VAR(values, p = 3L, type = "const")
expected <- as.numeric(predict(native, n.ahead = 1)$fcst$ES[1, "fcst"])
stopifnot(custom$status == "ok", abs(custom$predicted_log - expected) < 1e-10,
          abs(custom$root - max(vars::roots(native))) < 1e-10)
diff_spec <- spec; diff_spec$difference <- TRUE
diff_custom <- one_forecast(values, dates, diff_spec)
diff_native <- vars::VAR(apply(values, 2, diff), p = spec$p, type = "const")
diff_expected <- tail(values[, "ES"], 1) + as.numeric(predict(diff_native, n.ahead = 1)$fcst$ES[1, "fcst"])
stopifnot(diff_custom$status == "ok", abs(diff_custom$predicted_log - diff_expected) < 1e-10)
equation_data <- data.frame(y = native$datamat[, "ES"], native$datamat[, -(1:3), drop = FALSE])
rebuilt <- lm(y ~ . - 1, data = equation_data)
stopifnot(isTRUE(all.equal(unname(coef(rebuilt)), unname(coef(native$varresult$ES)), tolerance = 1e-12)),
          all(dim(sandwich::NeweyWest(rebuilt, prewhite = FALSE, adjust = TRUE)) == length(coef(rebuilt))))
chosen <- select_orders(values, 8)
native_order <- vars::VARselect(values, lag.max = 8, type = "const")$selection
stopifnot(chosen$bic == as.integer(native_order["SC(n)"]), chosen$aic == as.integer(native_order["AIC(n)"]))
five <- cbind(values, C = rnorm(nrow(values), -8, .7), NG = rnorm(nrow(values), -8, .7))
five[80, "C"] <- NA
full_spec <- spec
base_spec <- spec; base_spec$model <- "VAR_base_match_BIC"; base_spec$subset_symbols <- "ES/CL/GC"
full_fit <- one_forecast(five, dates, full_spec)
base_fit <- one_forecast(five, dates, base_spec)
stopifnot(full_fit$fitted_rows == base_fit$fitted_rows,
          full_fit$omitted_rows == base_fit$omitted_rows,
          base_fit$parameters < full_fit$parameters)

zero <- data.frame(model = "AR_selected", kind = "AR", p = 0L, difference = FALSE)
intercept <- one_forecast(values, dates, zero)
stopifnot(abs(intercept$predicted_log - mean(values[, "ES"])) < 1e-12,
          abs(intercept$predicted_variance - mean(exp(values[, "ES"]))) < 1e-12)

forecast_dates <- dates[seq_len(180)]
history <- values[seq_len(180), ]
first <- forecast_sequence(history, forecast_dates, spec, forecast_dates[160])
changed <- history
changed[161:180, ] <- changed[161:180, ] + 4
second <- forecast_sequence(changed, forecast_dates, spec, forecast_dates[160])
fields <- c("predicted_log", "predicted_variance", "smearing", "root", "fitted_rows", "status")
stopifnot(isTRUE(all.equal(first[1, fields], second[1, fields], tolerance = 1e-12)),
          first$date[1] == forecast_dates[161], first$origin_date[1] == forecast_dates[160],
          first$actual_log[1] != second$actual_log[1])

unavailable <- values; unavailable[nrow(values), "CL"] <- NA
fallback <- one_forecast(unavailable, dates, spec)
stopifnot(fallback$status == "fallback_persistence", fallback$detail == "Required origin predictors unavailable",
          fallback$predicted_log == tail(values[, "ES"], 1), fallback$predicted_variance > 0)
mask_date <- dates[60]
masked <- one_forecast(values, dates, spec, suspect_dates = mask_date, mask_span = 22)
stopifnot(masked$omitted_rows == 22, masked$fitted_rows == nrow(values) - spec$p - 22)
masked_own <- one_forecast(values, dates, zero, suspect_dates = mask_date, mask_span = 22)
stopifnot(masked_own$omitted_rows == 22,
          abs(masked_own$predicted_log - mean(values[-(60:81), "ES"])) < 1e-12)

rank_bad <- values; rank_bad[, "GC"] <- rank_bad[, "CL"]
failed <- one_forecast(rank_bad, dates, spec)
stopifnot(failed$status == "fallback_persistence", failed$detail == "Rank-deficient regression")

unstable_history <- values
unstable_history[, "ES"] <- 1.01^seq_len(nrow(values))
unstable_spec <- data.frame(model = "AR_selected", kind = "AR", p = 1L, difference = FALSE)
unstable <- one_forecast(unstable_history, dates, unstable_spec)
stopifnot(unstable$status == "fallback_persistence", unstable$detail == "Unstable fitted dynamics",
          unstable$root >= 1, unstable$predicted_log == tail(unstable_history[, "ES"], 1))

cat("VAR tests passed: native forecasts/roots/lag choices, AR(0), smearing, future invariance, dates, missing predictors, masking and failed-fit fallback.\n")
