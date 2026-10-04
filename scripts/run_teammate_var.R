# Usage: Rscript --vanilla scripts/run_teammate_var.R [output-directory]
# This reproduces the teammate's draft assumptions, not an approved final design.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])
stopifnot(length(script) == 1L)
PROJECT_ROOT <- dirname(dirname(normalizePath(script)))
cli <- commandArgs(trailingOnly = TRUE)
OUTPUT_DIR <- if (length(cli)) cli[1] else file.path(PROJECT_ROOT, "reports", "teammate_var")
dir.create(OUTPUT_DIR, recursive = TRUE, showWarnings = FALSE)
OUTPUT_DIR <- normalizePath(OUTPUT_DIR)
required <- c("urca", "vars", "sandwich")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Install required R packages: ", paste(missing, collapse = ", "))

run <- function() {
  pdf(file.path(OUTPUT_DIR, "diagnostic_plots.pdf"), width = 9, height = 8)
  on.exit(dev.off(), add = TRUE)
  sink(file.path(OUTPUT_DIR, "console_output.txt"), split = FALSE)
  on.exit(sink(), add = TRUE)
  state <- new.env(parent = globalenv())
  state$PROJECT_ROOT <- PROJECT_ROOT
  state$OUTPUT_DIR <- OUTPUT_DIR
  source(file.path(PROJECT_ROOT, "timadditions", "var_analysis.R"),
         local = state, echo = TRUE, print.eval = TRUE, max.deparse.length = Inf)
  save_csv <- function(value, name) write.csv(value, file.path(OUTPUT_DIR, name), row.names = FALSE)
  f <- state$FORECASTS
  f$origin_date <- head(state$ALL_DATA$date, -1)[state$n_initial:(nrow(state$ALL_DATA) - 1)]
  f$training_end <- f$origin_date
  f$training_observations <- state$n_initial + seq_len(nrow(f)) - 1L
  f$status <- "ok"
  stopifnot(all(f$origin_date < f$date), !anyDuplicated(f$date),
            isTRUE(all.equal(as.numeric(f[1, c("AR", "VAR", "Naive")]),
                            as.numeric(state$FIRST_FORECAST$forecast), tolerance = 1e-10)))
  save_csv(f, "forecasts.csv")
  save_csv(state$ACCURACY, "forecast_metrics.csv")
  save_csv(state$CW_RESULTS, "clark_west.csv")
  save_csv(state$YEARLY_ACCURACY, "yearly_accuracy.csv")
  save_csv(state$RV_SAMPLE, "sample_variance.csv")
  save_csv(state$MODEL_DATA[state$MODEL_DATA$date >= as.Date("2011-01-01") &
                            !complete.cases(state$MODEL_DATA), ], "excluded_incomplete_dates.csv")
  save_csv(data.frame(sample = c("training", "test"),
                     observations = c(nrow(state$TRAIN_DATA), nrow(state$TEST_DATA)),
                     start = c(min(state$TRAIN_DATA$date), min(state$TEST_DATA$date)),
                     end = c(max(state$TRAIN_DATA$date), max(state$TEST_DATA$date))), "sample_split.csv")
  loss <- data.frame(date = f$date)
  for (j in seq_len(nrow(state$MODEL_PAIRS))) {
    pair <- state$MODEL_PAIRS[j, ]
    raw <- (f$actual - f[[pair$ar]])^2 - (f$actual - f[[pair$var]])^2
    loss[[paste0(pair$ar, "_minus_", pair$var)]] <- raw
    loss[[paste0(pair$ar, "_minus_", pair$var, "_CW")]] <- raw + (f[[pair$ar]] - f[[pair$var]])^2
  }
  save_csv(loss, "paired_losses.csv")
  capture.output(sessionInfo(), file = file.path(OUTPUT_DIR, "sessionInfo.txt"))
  inputs <- file.path(PROJECT_ROOT, c("datasets/realized_variance_futures.csv",
                                    "timadditions/var_analysis.R", "scripts/run_teammate_var.R"))
  save_csv(data.frame(file = basename(inputs), md5 = unname(tools::md5sum(inputs))), "run_inputs.csv")
  config <- list(target = "log(rv5_ES), decimal-return variance", symbols = c("ES", "CL", "GC"),
                 sample_start = "2011-01-01", matching = "complete ES/CL/GC dates",
                 horizon = "next jointly observed row; provider session timing unverified",
                 train_fraction = .8, refit = "expanding, each target", max_lag = 20,
                 ar_order = state$p_ar, var_order = state$p_selected,
                 alternatives = c(15, 4, 14), variance_backtransform = FALSE,
                 generated_at = format(Sys.time(), tz = "Europe/Amsterdam", usetz = TRUE),
                 code_revision = system2("git", c("-C", shQuote(PROJECT_ROOT), "rev-parse", "HEAD"), stdout = TRUE),
                 note = "Hashes identify working files; revision alone does not include uncommitted changes.")
  dput(config, file = file.path(OUTPUT_DIR, "run_config.R"))
  # Regression checks against the rounded numbers in the supplied draft.
  expected <- c(AR=.4328876, VAR=.4356551, AR15=.4296496, VAR15=.4328146,
                AR_D4=.4501892, VAR_D4=.4524269, AR_D14=.4369072, VAR_D14=.4399775,
                Naive=.5267887)
  comparison <- state$ACCURACY
  comparison$draft_MSE <- unname(expected[comparison$model])
  comparison$absolute_difference <- abs(comparison$MSE - comparison$draft_MSE)
  comparison$matches_rounding <- comparison$absolute_difference <= 5.1e-8
  save_csv(comparison, "draft_number_comparison.csv")
  cat("\nDraft MSE values match rounding: ", all(comparison$matches_rounding), "\n")
}
run()
message("Completed. Outputs: ", OUTPUT_DIR)
