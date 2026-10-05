# Usage: Rscript --vanilla scripts/verify_var.R [generated-output-directory]
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])
root <- dirname(dirname(normalizePath(script)))
cli <- commandArgs(trailingOnly = TRUE)
out <- if (length(cli)) cli[1] else file.path(root, "reports", "var_final", "generated")
read <- function(name) read.csv(file.path(out, paste0(name, ".csv")), stringsAsFactors = FALSE)
panel <- read("main_variance_panel")
metrics <- read("forecast_metrics")
comparisons <- read("forecast_comparisons")
cfg <- jsonlite::fromJSON(file.path(root, "config", "var_analysis.json"))
raw <- read.csv(file.path(root, "datasets", "realized_variance_futures.csv"), stringsAsFactors = FALSE)
es_source <- raw[raw$symbol == "ES", ]
targets <- as.Date(panel$date[panel$date > "2023-07-12"])
origin <- as.Date(panel$date[match(as.character(targets), panel$date) - 1L])
stopifnot(length(targets) == 809L)
for (scenario in unique(metrics$scenario)) {
  f <- read(paste0(scenario, "_forecasts"))
  measure <- if (scenario == "rk") cfg$robustness_measure else cfg$primary_measure
  stopifnot(isTRUE(all.equal(f$actual_variance,
    es_source[[measure]][match(f$date, es_source$date)], tolerance = 1e-12)))
  stopifnot(!anyDuplicated(f[, c("date", "model")]),
            all(as.Date(f$origin_date) < as.Date(f$date)),
            all(f$training_end == f$origin_date),
            all(is.finite(f$predicted_log)), all(is.finite(f$predicted_variance)),
            all(f$predicted_variance > 0), all(f$smearing > 0))
  for (model in unique(f$model)) {
    z <- f[f$model == model, ]; metric <- metrics[metrics$scenario == scenario & metrics$model == model, ]
    stopifnot(identical(as.Date(z$date), targets), identical(as.Date(z$origin_date), origin))
    log_error <- z$actual_log - z$predicted_log
    ratio <- z$actual_variance / z$predicted_variance
    computed <- c(mean(log_error^2), sqrt(mean(log_error^2)), mean(abs(log_error)),
                  mean((z$actual_variance - z$predicted_variance)^2), mean(ratio - log(ratio) - 1))
    saved <- as.numeric(metric[1, c("log_MSE", "log_RMSE", "log_MAE", "variance_MSE", "QLIKE")])
    stopifnot(isTRUE(all.equal(computed, saved, tolerance = 1e-10)))
    regular <- z$status == "ok"
    stopifnot(isTRUE(all.equal(z$predicted_variance[regular],
                              exp(z$predicted_log[regular]) * z$smearing[regular], tolerance = 1e-12)))
    fallback <- !regular
    if (any(fallback)) stopifnot(all(z$smearing[fallback] == 1),
      all(z$status[fallback] == "fallback_persistence"),
      isTRUE(all.equal(z$predicted_variance[fallback],
        es_source[[measure]][match(z$origin_date[fallback], es_source$date)], tolerance = 1e-12)))
  }
  scenario_pairs <- comparisons[comparisons$scenario == scenario, ]
  for (j in seq_len(nrow(scenario_pairs))) {
    pair <- scenario_pairs[j, ]; a <- f[f$model == pair$AR, ]; v <- f[f$model == pair$VAR, ]
    adjusted <- (a$actual_log - a$predicted_log)^2 - (v$actual_log - v$predicted_log)^2 +
      (a$predicted_log - v$predicted_log)^2
    stopifnot(abs(mean(adjusted) - pair$mean_adjusted_difference) < 1e-12)
    if (all(a$status == "ok" & v$status == "ok")) {
      # Rebuild Bartlett long-run variance directly, independently of vcov().
      fit <- lm(adjusted ~ 1); u <- adjusted - mean(adjusted); n <- length(u)
      bandwidth <- floor(sandwich::bwNeweyWest(fit, prewhite = FALSE))
      long_run <- sum(u^2) / n
      if (bandwidth > 0) for (lag in seq_len(bandwidth))
        long_run <- long_run + 2 * (1 - lag / (bandwidth + 1)) * sum(u[(lag + 1):n] * u[1:(n - lag)]) / n
      statistic <- mean(adjusted) / sqrt(long_run / (n - 1))
      stopifnot(abs(statistic - pair$CW_statistic) < 1e-10,
                abs(pnorm(statistic, lower.tail = FALSE) - pair$p_one_sided) < 1e-10)
    } else stopifnot(is.na(pair$CW_statistic), is.na(pair$p_one_sided),
                    pair$inference_status == "withheld_due_to_fallbacks")
  }
  stopifnot(isTRUE(all.equal(scenario_pairs$p_Holm,
                            p.adjust(scenario_pairs$p_one_sided, "holm"), tolerance = 1e-12)))
}
main <- read("main_forecasts")
stationarity <- read("stationarity")
stopifnot(all(is.finite(stationarity$KPSS_critical_5pct)),
          all(is.finite(stationarity$ADF_critical_5pct)))
expected_mse <- c(AR_selected=.4328876, AR_match_BIC=.4328876, VAR_BIC=.4356551,
                 AR_match_AIC=.4296496, VAR_AIC=.4328146, AR_diff_BIC=.4501892,
                 VAR_diff_BIC=.4524269, AR_diff_AIC=.4369072, VAR_diff_AIC=.4399775, Persistence=.5267887)
main_metrics <- metrics[metrics$scenario == "main", ]
stopifnot(all(abs(main_metrics$log_MSE - expected_mse[main_metrics$model]) < 5.1e-8),
          all(main_metrics$fallbacks == 0))
legacy <- file.path(root, "reports", "teammate_var", "forecasts.csv")
if (file.exists(legacy)) {
  old <- read.csv(legacy)
  mapping <- c(AR_selected="AR", AR_match_BIC="AR", VAR_BIC="VAR", AR_match_AIC="AR15", VAR_AIC="VAR15",
               AR_diff_BIC="AR_D4", VAR_diff_BIC="VAR_D4", AR_diff_AIC="AR_D14", VAR_diff_AIC="VAR_D14", Persistence="Naive")
  for (name in names(mapping)) stopifnot(max(abs(main$predicted_log[main$model == name] - old[[mapping[name]]])) < 1e-10)
}
extension <- read("corn_gas_forecasts")
for (pair in list(c("VAR_base_match_BIC", "VAR_BIC"), c("VAR_base_match_AIC", "VAR_AIC"))) {
  a <- extension[extension$model == pair[1], ]; b <- extension[extension$model == pair[2], ]
  stopifnot(identical(a$date, b$date), identical(a$p, b$p), identical(a$fitted_rows, b$fitted_rows))
}
manifest <- jsonlite::fromJSON(file.path(out, "provenance.json"))
input_paths <- c(realized_variance_futures.csv = file.path(root, "datasets", "realized_variance_futures.csv"),
                 var_analysis.json = file.path(root, "config", "var_analysis.json"),
                 var_pipeline.R = file.path(root, "R", "var_pipeline.R"), run_var.R = file.path(root, "scripts", "run_var.R"))
for (name in names(input_paths)) stopifnot(digest::digest(file = input_paths[name], algo = "sha256") == manifest$input_sha256[[name]])
for (name in names(manifest$output_sha256)) stopifnot(digest::digest(file = file.path(out, name), algo = "sha256") == manifest$output_sha256[[name]])
cat("Verified all scenario targets/origins, raw ES targets, fallback values, finite forecasts, loss arithmetic, direct Bartlett CW statistics/Holm adjustment, smearing, original MSE/forecast reproduction, matched extension training rows and SHA-256 provenance.\n")
