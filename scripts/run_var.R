# Usage: Rscript --vanilla scripts/run_var.R [output-directory]
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])
ROOT <- dirname(dirname(normalizePath(script)))
cli <- commandArgs(trailingOnly = TRUE)
output <- if (length(cli)) cli[1] else file.path(ROOT, "reports", "var_final", "generated")
dir.create(output, recursive = TRUE, showWarnings = FALSE)
output <- normalizePath(output)
required <- c("vars", "urca", "sandwich", "jsonlite", "digest")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Install R packages: ", paste(missing, collapse = ", "))
source(file.path(ROOT, "R", "var_pipeline.R"))
config_path <- file.path(ROOT, "config", "var_analysis.json")
cfg <- jsonlite::fromJSON(config_path)
source_path <- file.path(ROOT, "datasets", "realized_variance_futures.csv")
source_hash <- digest::digest(file = source_path, algo = "sha256")
raw <- read.csv(source_path, stringsAsFactors = FALSE)
raw$date <- as.Date(raw$date, format = "%Y-%m-%d")
stopifnot(!anyNA(raw$date), !anyDuplicated(raw[, c("date", "symbol")]),
          all(c(cfg$main_symbols, cfg$extension_symbols) %in% raw$symbol))
make_wide <- function(measure, symbols) {
  d <- raw[raw$symbol %in% symbols, c("date", "symbol", measure)]
  z <- reshape(d, idvar = "date", timevar = "symbol", direction = "wide")
  names(z) <- sub(paste0("^", measure, "\\."), "", names(z))
  z <- z[order(z$date), c("date", symbols)]
  z[z$date >= cfg$sample_start & z$date <= cfg$test_end, ]
}
rv <- make_wide(cfg$primary_measure, cfg$main_symbols)
missing_grid <- rv[!complete.cases(rv), ]
write.csv(missing_grid, file.path(output, "main_absent_dates.csv"), row.names = FALSE)
panel <- rv[complete.cases(rv), ]; rownames(panel) <- NULL
dates <- panel$date
stopifnot(sum(dates > cfg$training_end) == 809L, tail(dates, 1) == as.Date(cfg$test_end),
          min(dates[dates > cfg$training_end]) == as.Date("2023-07-13"))
build_logs <- function(measure, symbols) {
  d <- make_wide(measure, symbols)
  d <- d[match(dates, d$date), symbols, drop = FALSE]
  values <- as.matrix(d)
  if (any(!is.finite(values[!is.na(values)])) || any(values <= 0, na.rm = TRUE))
    stop("Variance values must be finite and positive when observed")
  log(values)
}
save_csv <- function(value, name) write.csv(value, file.path(output, paste0(name, ".csv")), row.names = FALSE)
scenarios <- list(
  main = list(measure = cfg$primary_measure, symbols = cfg$main_symbols, suspects = as.Date(character())),
  rk = list(measure = cfg$robustness_measure, symbols = cfg$main_symbols, suspects = as.Date(character())),
  suspect_training = list(measure = cfg$primary_measure, symbols = cfg$main_symbols, suspects = as.Date(cfg$suspect_dates)),
  corn_gas = list(measure = cfg$primary_measure, symbols = cfg$extension_symbols, suspects = as.Date(character())))
all_metrics <- all_specs <- all_pairs <- all_years <- all_flow <- list()
main_forecasts <- NULL
for (name in names(scenarios)) {
  scenario <- scenarios[[name]]
  message("Running VAR scenario: ", name)
  logs <- build_logs(scenario$measure, scenario$symbols)
  training <- logs[dates <= cfg$training_end, , drop = FALSE]
  selection <- model_specs(training, cfg$max_lag)
  # The anomaly run changes estimation rows, not the already chosen model ladder.
  if (name == "suspect_training") selection <- main_selection
  if (name == "main") main_selection <- selection
  specs <- selection$specs
  if (name == "corn_gas") {
    specs$subset_symbols <- ""
    controls <- specs[specs$model %in% c("VAR_BIC", "VAR_AIC"), ]
    controls$model <- c("VAR_base_match_BIC", "VAR_base_match_AIC")
    controls$subset_symbols <- paste(cfg$main_symbols, collapse = "/")
    specs <- rbind(specs, controls)
  } else specs$subset_symbols <- ""
  save_csv(selection$selection, paste0(name, "_lag_selection"))
  if (name == "main") {
    diagnostic <- initial_diagnostics(training, dates[dates <= cfg$training_end], specs, output)
    save_csv(diagnostic$diagnostics, "training_diagnostics")
    save_csv(diagnostic$stationarity, "stationarity")
    save_csv(diagnostic$joint, "joint_predictive_tests")
    save_csv(panel, "main_variance_panel")
  }
  f <- forecast_sequence(logs, dates, specs, as.Date(cfg$training_end), scenario$suspects, cfg$max_lag + 2L)
  save_csv(f, paste0(name, "_forecasts"))
  metrics <- score_forecasts(f); metrics$scenario <- name
  specs$scenario <- name
  pair <- compare_pairs(f); pair$comparisons$scenario <- name
  save_csv(pair$losses, paste0(name, "_paired_losses"))
  influence <- do.call(rbind, lapply(split(pair$losses, paste(pair$losses$AR, pair$losses$VAR)), function(z) {
    z[order(abs(z$raw_loss_difference), decreasing = TRUE)[seq_len(min(10L, nrow(z)))], ]
  }))
  save_csv(influence, paste0(name, "_influential_dates"))
  sensitivity <- do.call(rbind, lapply(split(pair$losses, paste(pair$losses$AR, pair$losses$VAR)), function(z) {
    drop <- order(abs(z$raw_loss_difference), decreasing = TRUE)[seq_len(5L)]
    data.frame(benchmark = z$AR[1], VAR = z$VAR[1], targets = nrow(z),
      mean_raw_gain = mean(z$raw_loss_difference), removed = length(drop),
      mean_raw_gain_without_top5 = mean(z$raw_loss_difference[-drop]),
      interpretation = "Retrospective influence check only; no evaluation dates removed from main scores")
  }))
  save_csv(sensitivity, paste0(name, "_influence_summary"))
  all_metrics[[name]] <- metrics; all_specs[[name]] <- specs
  all_pairs[[name]] <- pair$comparisons
  all_flow[[name]] <- data.frame(scenario = name, symbols = paste(scenario$symbols, collapse = "/"),
    measure = scenario$measure, source_grid_rows = nrow(panel), initial_history = nrow(training),
    test_targets = length(unique(f$date)), missing_cells = sum(is.na(logs)),
    fallback_predictions = sum(f$status != "ok"))
  for (year in unique(format(f$date, "%Y"))) {
    z <- score_forecasts(f[format(f$date, "%Y") == year, ]); z$year <- year; z$scenario <- name
    all_years[[length(all_years) + 1L]] <- z
  }
  if (name == "main") main_forecasts <- f
  if (name == "corn_gas") {
    # Secondary comparison on origins where both AR/VAR actually fit, with explicit counts.
    eligible <- do.call(rbind, lapply(split(f, f$date), function(z) {
      if (all(z$status == "ok")) z else NULL
    }))
    save_csv(score_forecasts(eligible), "corn_gas_all_models_available_metrics")
    matched_dates <- unique(eligible$date)
    save_csv(score_forecasts(main_forecasts[main_forecasts$date %in% matched_dates, ]),
             "main_on_extension_available_dates_metrics")
  }
}
metrics <- do.call(rbind, all_metrics); pairs <- do.call(rbind, all_pairs)
# Each scenario is a separate exploratory family (four comparisons; six for the extension).
pairs$p_Holm <- ave(pairs$p_one_sided, pairs$scenario, FUN = function(x) p.adjust(x, "holm"))
save_csv(metrics, "forecast_metrics"); save_csv(do.call(rbind, all_specs), "model_specs")
save_csv(pairs, "forecast_comparisons"); save_csv(do.call(rbind, all_years), "yearly_metrics")
save_csv(do.call(rbind, all_flow), "sample_flow")
status <- do.call(rbind, lapply(names(scenarios), function(name) {
  f <- read.csv(file.path(output, paste0(name, "_forecasts.csv")))
  f$detail[is.na(f$detail)] <- ""
  z <- aggregate(list(predictions = f$model), f[, c("model", "status", "detail")], length)
  z$scenario <- rep(name, nrow(z)); z
}))
save_csv(status, "fit_status_summary")
pdf(file.path(output, "forecast_figures.pdf"), width = 10, height = 6)
for (name in c("VAR_BIC", "VAR_AIC")) {
  benchmark <- if (name == "VAR_BIC") "AR_match_BIC" else "AR_match_AIC"
  a <- main_forecasts[main_forecasts$model == benchmark, ]
  v <- main_forecasts[main_forecasts$model == name, ]
  loss <- (a$actual_log - a$predicted_log)^2 - (v$actual_log - v$predicted_log)^2
  plot(v$date, cumsum(loss), type = "l", col = "#235789", lwd = 1.5,
       main = paste(name, "cumulative advantage against", benchmark),
       xlab = "Target provider date", ylab = "Cumulative AR squared error minus VAR squared error")
  abline(h = 0, lty = 2, col = "grey60")
}
v <- main_forecasts[main_forecasts$model == "VAR_BIC", ]
plot(v$date, v$actual_log, type = "l", col = "grey60", main = "VAR BIC: log-variance targets and forecasts",
     xlab = "Target provider date", ylab = "log RV5 variance")
lines(v$date, v$predicted_log, col = "#235789", lwd = 1.2)
legend("topleft", c("Actual", "VAR forecast"), col = c("grey60", "#235789"), lty = 1, bty = "n")
dev.off()
capture.output(sessionInfo(), file = file.path(output, "sessionInfo.txt"))
inputs <- c(source_path, config_path, file.path(ROOT, "R", "var_pipeline.R"), normalizePath(script))
manifest <- list(config = cfg, input_sha256 = setNames(lapply(inputs, function(p) digest::digest(file = p, algo = "sha256")), basename(inputs)),
  generated_at = format(Sys.time(), tz = "Europe/Amsterdam", usetz = TRUE),
  output_sha256 = setNames(lapply(list.files(output, full.names = TRUE)[list.files(output) != "provenance.json"], function(p) digest::digest(file = p, algo = "sha256")), list.files(output)[list.files(output) != "provenance.json"]),
  code_revision = system2("git", c("-C", shQuote(ROOT), "rev-parse", "HEAD"), stdout = TRUE),
  calendar_verified = FALSE, main_grid = "explicit next common ES/CL/GC observation; no additional extension-date compression")
jsonlite::write_json(manifest, file.path(output, "provenance.json"), pretty = TRUE, auto_unbox = TRUE)
stopifnot(digest::digest(file = source_path, algo = "sha256") == source_hash)
print(metrics[metrics$scenario == "main", ])
message("Completed VAR outputs: ", output)
