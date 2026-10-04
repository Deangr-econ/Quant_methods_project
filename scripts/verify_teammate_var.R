# Verify a completed reproduction against the supplied draft and dated inputs.
# Usage: Rscript --vanilla scripts/verify_teammate_var.R [output-directory]
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])
root <- dirname(dirname(normalizePath(script)))
cli <- commandArgs(trailingOnly = TRUE)
out <- if (length(cli)) cli[1] else file.path(root, "reports", "teammate_var")
read <- function(name) read.csv(file.path(out, name))
f <- read("forecasts.csv")
sample <- read("sample_variance.csv")
split <- read("sample_split.csv")
stopifnot(nrow(f) == 809L, f$date[1] == "2023-07-13",
          all(read("draft_number_comparison.csv")$matches_rounding),
          all(as.Date(f$origin_date) < as.Date(f$date)), !anyDuplicated(f$date),
          all(f$training_end == f$origin_date), all(f$status == "ok"))
initial <- split$observations[1]
stopifnot(identical(f$date, tail(sample$date, nrow(f))),
          identical(f$origin_date, sample$date[initial:(nrow(sample) - 1)]),
          isTRUE(all.equal(f$actual, log(tail(sample$ES, nrow(f))), tolerance = 1e-12)),
          isTRUE(all.equal(f$Naive, log(sample$ES[initial:(nrow(sample) - 1)]), tolerance = 1e-12)))
accuracy <- read("forecast_metrics.csv")
for (i in seq_len(nrow(accuracy))) {
  errors <- f$actual - f[[accuracy$model[i]]]
  stopifnot(isTRUE(all.equal(c(mean(errors^2), sqrt(mean(errors^2)), mean(abs(errors))),
                            as.numeric(accuracy[i, c("MSE", "RMSE", "MAE")]), tolerance = 1e-12)))
}
cw <- read("clark_west.csv")
stopifnot(all(abs(cw$p_one_sided - c(.4542865, .2485564, .4108747, .2375906)) < 5.1e-8),
          all(abs(cw$p_Holm - .9503624) < 5.1e-8))
annual <- read("yearly_accuracy.csv")
stopifnot(identical(as.integer(annual$observations), c(121L, 259L, 258L, 171L)),
          abs(weighted.mean(annual$AR_MSE, annual$observations) - accuracy$MSE[accuracy$model == "AR"]) < 1e-12)
# Exercise the intercept-only AR candidate without rerunning the full analysis.
expressions <- parse(file.path(root, "timadditions", "var_analysis.R"))
helper <- Filter(function(x) is.call(x) && identical(x[[1]], as.name("<-")) &&
                   identical(x[[2]], as.name("AR_ONE_STEP")), as.list(expressions))
stopifnot(length(helper) == 1L)
eval(helper[[1]])
stopifnot(AR_ONE_STEP(c(1, 3, 5), 0) == 3)
cat("Verified: draft MSE/CW values, all loss calculations, dates, persistence target, annual counts and AR(0).\n")
