setwd("C:/Users/tschm/OneDrive/Desktop/Maastricht Uni/Quantitative Techniques/R")
getwd()

VOLARE_DATA <- rio::import("data/realized_variance_futures.csv")

# Number of rows and columns
dim(VOLARE_DATA)

# Variable names
names(VOLARE_DATA)

# Structure of the three columns we initially need
str(VOLARE_DATA[, c("date", "symbol", "rv5")])

# First observations
head(VOLARE_DATA[, c("date", "symbol", "rv5")])

# Number of observations for each futures market
table(VOLARE_DATA$symbol)

# Keep the three columns we need
RV_DATA <- VOLARE_DATA[, c("date", "symbol", "rv5")]

# Use standard R dates
RV_DATA$date <- as.Date(RV_DATA$date)

# Check that each market has only one observation per date
anyDuplicated(RV_DATA[, c("date", "symbol")])

# Convert from one market per row to one market per column
RV_WIDE <- reshape(
  RV_DATA,
  idvar = "date",
  timevar = "symbol",
  direction = "wide"
)

# Rename columns: rv5.ES becomes ES, etc.
names(RV_WIDE) <- sub("^rv5\\.", "", names(RV_WIDE))

# Arrange dates chronologically and reorder the columns
RV_WIDE <- RV_WIDE[order(RV_WIDE$date),
                   c("date", "ES", "CL", "GC", "NG", "C")]

rownames(RV_WIDE) <- NULL

# Inspect the result
head(RV_WIDE)

# Count missing observations in each column
colSums(is.na(RV_WIDE))

# Create a separate dataset for our initial three-market model
MODEL_DATA <- RV_WIDE[, c("date", "ES", "CL", "GC")]

# Identify dates with at least one missing observation
missing_dates <- !complete.cases(MODEL_DATA)

# How many dates are affected?
sum(missing_dates)

# Which dates and markets are affected?
MODEL_DATA[missing_dates, ]

# How many complete observations are available?
sum(!missing_dates)

# Extract gold observations from the original dataset
GOLD_CHECK <- VOLARE_DATA[
  VOLARE_DATA$symbol == "GC",
  c("date", "rv5", "open_price", "close_price",
    "high_price", "low_price")
]

# Show the five observations with the largest realised variance
head(
  GOLD_CHECK[order(GOLD_CHECK$rv5, decreasing = TRUE), ],
  5
)

print(
  head(
    GOLD_CHECK[order(GOLD_CHECK$rv5, decreasing = TRUE), ],
    5
  )
)

# Keep observations from January 2011 onwards
RV_SAMPLE <- MODEL_DATA[
  MODEL_DATA$date >= as.Date("2011-01-01"),
]

# Check how many dates are incomplete within this period
sum(!complete.cases(RV_SAMPLE))

# Keep dates with observations for all three markets
RV_SAMPLE <- RV_SAMPLE[complete.cases(RV_SAMPLE), ]

rownames(RV_SAMPLE) <- NULL

# Check sample size and date range
nrow(RV_SAMPLE)
range(RV_SAMPLE$date)

sapply(
  RV_SAMPLE[, c("ES", "CL", "GC")],
  function(x) all(is.finite(x) & x > 0)
)

# Five largest equity variance observations
head(RV_SAMPLE[order(RV_SAMPLE$ES, decreasing = TRUE), ], 5)

# Five largest oil variance observations
head(RV_SAMPLE[order(RV_SAMPLE$CL, decreasing = TRUE), ], 5)

# Inspect prices associated with the five largest oil variances
OIL_CHECK <- VOLARE_DATA[
  VOLARE_DATA$symbol == "CL" &
    VOLARE_DATA$date >= as.Date("2011-01-01"),
  c("date", "rv5", "open_price", "close_price",
    "high_price", "low_price")
]

head(OIL_CHECK[order(OIL_CHECK$rv5, decreasing = TRUE), ], 5)

# Make a separate copy for log realised variance
LOG_RV <- RV_SAMPLE

# Apply the natural logarithm to each variance column
LOG_RV[, c("ES", "CL", "GC")] <- lapply(
  RV_SAMPLE[, c("ES", "CL", "GC")],
  log
)

# Inspect the transformed observations
head(LOG_RV)

# Summarise each transformed series
summary(LOG_RV[, c("ES", "CL", "GC")])

# Number of observations allocated to training
n_train <- floor(0.80 * nrow(LOG_RV))

# First 80%: training sample
TRAIN_DATA <- LOG_RV[seq_len(n_train), ]

# Final 20%: test sample
TEST_DATA <- LOG_RV[
  (n_train + 1):nrow(LOG_RV),
]

# Summarise the split
data.frame(
  sample = c("Training", "Test"),
  observations = c(nrow(TRAIN_DATA), nrow(TEST_DATA)),
  start = c(min(TRAIN_DATA$date), min(TEST_DATA$date)),
  end = c(max(TRAIN_DATA$date), max(TEST_DATA$date))
)

# Display three plots above one another
par(mfrow = c(3, 1))

for (market in c("ES", "CL", "GC")) {
  plot(
    TRAIN_DATA$date,
    TRAIN_DATA[[market]],
    type = "l",
    main = paste(market, "- training sample"),
    xlab = "Date",
    ylab = "Log realised variance"
  )
}

# Restore the usual single-plot layout
par(mfrow = c(1, 1))

library(urca)

ADF_ES <- ur.df(
  TRAIN_DATA$ES,
  type = "drift",
  lags = 20,
  selectlags = "BIC"
)

summary(ADF_ES)

ADF_CL <- ur.df(
  TRAIN_DATA$CL,
  type = "drift",
  lags = 20,
  selectlags = "BIC"
)

ADF_GC <- ur.df(
  TRAIN_DATA$GC,
  type = "drift",
  lags = 20,
  selectlags = "BIC"
)

summary(ADF_CL)
summary(ADF_GC)

KPSS_ES <- ur.kpss(TRAIN_DATA$ES, type = "mu", lags = "long")
KPSS_CL <- ur.kpss(TRAIN_DATA$CL, type = "mu", lags = "long")
KPSS_GC <- ur.kpss(TRAIN_DATA$GC, type = "mu", lags = "long")

summary(KPSS_ES)
summary(KPSS_CL)
summary(KPSS_GC)

# Average log realised variance within each calendar year
ANNUAL_MEANS <- aggregate(
  TRAIN_DATA[, c("ES", "CL", "GC")],
  by = list(year = format(TRAIN_DATA$date, "%Y")),
  FUN = mean
)

ANNUAL_MEANS

# Examine persistence over 100 observed trading sessions
par(mfrow = c(3, 1))

for (market in c("ES", "CL", "GC")) {
  acf(
    TRAIN_DATA[[market]],
    lag.max = 100,
    main = paste("ACF of log realised variance:", market)
  )
}

par(mfrow = c(1, 1))

# Extract autocorrelations at selected lags
ACF_CHECK <- sapply(c("ES", "CL", "GC"), function(market) {
  
  correlations <- acf(
    TRAIN_DATA[[market]],
    lag.max = 100,
    plot = FALSE
  )$acf
  
  # First position is lag zero, so lag k is position k + 1
  as.numeric(correlations[c(2, 6, 21, 61, 101)])
})

rownames(ACF_CHECK) <- c("Lag 1", "Lag 5", "Lag 20",
                         "Lag 60", "Lag 100")

round(ACF_CHECK, 3)

KPSS_SENSITIVITY <- data.frame(lags = c(28, 56, 112))

for (market in c("ES", "CL", "GC")) {
  
  KPSS_SENSITIVITY[[market]] <- sapply(
    KPSS_SENSITIVITY$lags,
    function(L) {
      
      result <- ur.kpss(
        TRAIN_DATA[[market]],
        type = "mu",
        use.lag = L
      )
      
      as.numeric(result@teststat)
    }
  )
}

KPSS_SENSITIVITY

library(vars)

# Include only the three model variables; exclude the date column
VAR_TRAIN <- TRAIN_DATA[, c("ES", "CL", "GC")]

# Compare VAR models with 1 through 20 lags
LAG_SELECTION <- VARselect(
  VAR_TRAIN,
  lag.max = 20,
  type = "const"
)

# Display the lag order selected by each criterion
LAG_SELECTION$selection


# Extract the lag order selected by BIC
p_selected <- as.integer(LAG_SELECTION$selection["SC(n)"])

# Estimate our initial VAR
VAR_MODEL <- VAR(
  VAR_TRAIN,
  p = p_selected,
  type = "const"
)

# Display the equity equation
summary(VAR_MODEL$varresult$ES)

# 1. Dynamic stability of the fitted VAR
VAR_ROOTS <- roots(VAR_MODEL)

max(VAR_ROOTS)
all(VAR_ROOTS < 1)

# 2. Remaining serial correlation in the system's residuals
serial.test(
  VAR_MODEL,
  lags.pt = 30,
  type = "PT.adjusted"
)

# 3. Changes in residual variance: multivariate ARCH test
arch.test(
  VAR_MODEL,
  lags.multi = 5,
  multivariate.only = TRUE
)

# Estimate the alternative selected by AIC
VAR_MODEL_15 <- VAR(
  VAR_TRAIN,
  p = 15,
  type = "const"
)

# Check dynamic stability
max(roots(VAR_MODEL_15))
all(roots(VAR_MODEL_15) < 1)

# Check remaining serial correlation
serial.test(
  VAR_MODEL_15,
  lags.pt = 30,
  type = "PT.adjusted"
)

# Check dependence in residual error magnitudes
arch.test(
  VAR_MODEL_15,
  lags.multi = 5,
  multivariate.only = TRUE
)

# Calculate changes in each training series
DIFF_TRAIN <- as.data.frame(
  lapply(VAR_TRAIN, diff)
)

# Differencing loses the first observation
nrow(DIFF_TRAIN)
head(DIFF_TRAIN)

# Check stationarity evidence for the differenced series
DIFF_TESTS <- lapply(DIFF_TRAIN, function(x) {
  
  adf_result <- ur.df(
    x,
    type = "drift",
    lags = 20,
    selectlags = "BIC"
  )
  
  kpss_result <- ur.kpss(
    x,
    type = "mu",
    lags = "long"
  )
  
  c(
    ADF_tau2 = as.numeric(adf_result@teststat[1]),
    KPSS_stat = as.numeric(kpss_result@teststat)
  )
})

# Display one row per market
round(do.call(rbind, DIFF_TESTS), 4)

# Compare lag orders for the VAR in changes in log variance
DIFF_LAG_SELECTION <- VARselect(
  DIFF_TRAIN,
  lag.max = 20,
  type = "const"
)

DIFF_LAG_SELECTION$selection

# Extract the differenced VAR lag order selected by BIC
p_diff_selected <- as.integer(
  DIFF_LAG_SELECTION$selection["SC(n)"]
)

# Estimate the model
VAR_DIFF_MODEL <- VAR(
  DIFF_TRAIN,
  p = p_diff_selected,
  type = "const"
)

# Check dynamic stability
max(roots(VAR_DIFF_MODEL))
all(roots(VAR_DIFF_MODEL) < 1)

# Check remaining serial correlation
serial.test(
  VAR_DIFF_MODEL,
  lags.pt = 30,
  type = "PT.adjusted"
)

# Check dependence in residual error magnitudes
arch.test(
  VAR_DIFF_MODEL,
  lags.multi = 5,
  multivariate.only = TRUE
)

# Extract the lag order selected by AIC
p_diff_aic <- as.integer(
  DIFF_LAG_SELECTION$selection["AIC(n)"]
)

# Estimate the alternative differenced VAR
VAR_DIFF_MODEL_14 <- VAR(
  DIFF_TRAIN,
  p = p_diff_aic,
  type = "const"
)

# Dynamic stability
max(roots(VAR_DIFF_MODEL_14))
all(roots(VAR_DIFF_MODEL_14) < 1)

# Residual serial correlation
serial.test(
  VAR_DIFF_MODEL_14,
  lags.pt = 30,
  type = "PT.adjusted"
)

# Dependence in residual error magnitudes
arch.test(
  VAR_DIFF_MODEL_14,
  lags.multi = 5,
  multivariate.only = TRUE
)

# Construct current equity log variance and its previous 20 values
AR_DATA <- as.data.frame(embed(TRAIN_DATA$ES, 21))

names(AR_DATA) <- c("ES", paste0("lag", 1:20))

# Prepare storage for candidate models and their BIC values
AR_MODELS <- vector("list", 21)

AR_SELECTION <- data.frame(
  lag = 0:20,
  BIC = NA_real_
)

# Estimate each candidate using the same observations
for (p in 0:20) {
  
  if (p == 0) {
    ar_formula <- ES ~ 1
  } else {
    ar_formula <- reformulate(
      paste0("lag", seq_len(p)),
      response = "ES"
    )
  }
  
  fitted_model <- lm(ar_formula, data = AR_DATA)
  
  AR_MODELS[[p + 1]] <- fitted_model
  AR_SELECTION$BIC[p + 1] <- BIC(fitted_model)
}

# Select the model with the lowest BIC
p_ar <- AR_SELECTION$lag[which.min(AR_SELECTION$BIC)]

AR_MODEL <- AR_MODELS[[p_ar + 1]]

# Show the selected lag and five best candidates
p_ar

head(
  AR_SELECTION[order(AR_SELECTION$BIC), ],
  5
)

# Refit the selected AR using all available training observations
AR_REFIT_DATA <- as.data.frame(
  embed(TRAIN_DATA$ES, p_ar + 1)
)

names(AR_REFIT_DATA) <- c(
  "ES", paste0("lag", seq_len(p_ar))
)

AR_MODEL <- lm(ES ~ ., data = AR_REFIT_DATA)

# Prepare the latest five equity observations as predictors
AR_NEW_DATA <- as.data.frame(
  t(rev(tail(TRAIN_DATA$ES, p_ar)))
)

names(AR_NEW_DATA) <- paste0("lag", seq_len(p_ar))

# Equity-only forecast
AR_FIRST <- as.numeric(
  predict(AR_MODEL, newdata = AR_NEW_DATA)
)

# Cross-market VAR forecast
VAR_FIRST <- as.numeric(
  predict(VAR_MODEL, n.ahead = 1)$fcst$ES[1, "fcst"]
)

# Simple persistence forecast: tomorrow equals today's value
NAIVE_FIRST <- tail(TRAIN_DATA$ES, 1)

FIRST_FORECAST <- data.frame(
  date = TEST_DATA$date[1],
  model = c("AR(5)", "VAR(5)", "Last observation"),
  actual = TEST_DATA$ES[1],
  forecast = c(AR_FIRST, VAR_FIRST, NAIVE_FIRST)
)

FIRST_FORECAST$error <-
  FIRST_FORECAST$actual - FIRST_FORECAST$forecast

FIRST_FORECAST$squared_error <- FIRST_FORECAST$error^2

FIRST_FORECAST

# Combine the chronological samples
ALL_DATA <- rbind(TRAIN_DATA, TEST_DATA)

n_initial <- nrow(TRAIN_DATA)
n_test <- nrow(TEST_DATA)

# Prepare storage for forecasts
FORECASTS <- data.frame(
  date = TEST_DATA$date,
  actual = TEST_DATA$ES,
  AR = NA_real_,
  VAR = NA_real_,
  Naive = NA_real_
)

for (i in seq_len(n_test)) {
  
  # Last observation available BEFORE this forecast's target
  last_known <- n_initial + i - 1
  
  history <- ALL_DATA[seq_len(last_known), ]
  
  # Re-estimate the equity-only AR
  ar_data <- as.data.frame(embed(history$ES, p_ar + 1))
  names(ar_data) <- c("ES", paste0("lag", seq_len(p_ar)))
  
  ar_fit <- lm(ES ~ ., data = ar_data)
  
  ar_new <- as.data.frame(
    t(rev(tail(history$ES, p_ar)))
  )
  names(ar_new) <- paste0("lag", seq_len(p_ar))
  
  FORECASTS$AR[i] <- as.numeric(
    predict(ar_fit, newdata = ar_new)
  )
  
  # Re-estimate the cross-market VAR
  var_fit <- VAR(
    history[, c("ES", "CL", "GC")],
    p = p_selected,
    type = "const"
  )
  
  FORECASTS$VAR[i] <- as.numeric(
    predict(var_fit, n.ahead = 1)$fcst$ES[1, "fcst"]
  )
  
  # Persistence benchmark
  FORECASTS$Naive[i] <- tail(history$ES, 1)
  
  if (i %% 100 == 0) {
    message("Completed ", i, " of ", n_test, " forecasts")
  }
}

# Every model should have a finite forecast for every test date
stopifnot(
  all(is.finite(as.matrix(
    FORECASTS[, c("AR", "VAR", "Naive")]
  )))
)

head(FORECASTS)

ACCURACY <- do.call(
  rbind,
  lapply(c("AR", "VAR", "Naive"), function(model) {
    
    errors <- FORECASTS$actual - FORECASTS[[model]]
    
    data.frame(
      model = model,
      MSE = mean(errors^2),
      RMSE = sqrt(mean(errors^2)),
      MAE = mean(abs(errors))
    )
  })
)

ACCURACY

AR_ONE_STEP <- function(x, p) {
  
  if (p == 0) return(mean(x))
  
  lag_data <- as.data.frame(embed(x, p + 1))
  names(lag_data) <- c("ES", paste0("lag", seq_len(p)))
  
  fitted_ar <- lm(ES ~ ., data = lag_data)
  
  new_data <- as.data.frame(t(rev(tail(x, p))))
  names(new_data) <- paste0("lag", seq_len(p))
  
  as.numeric(predict(fitted_ar, newdata = new_data))
}

FORECASTS$AR15 <- NA_real_
FORECASTS$VAR15 <- NA_real_

for (i in seq_len(n_test)) {
  
  last_known <- n_initial + i - 1
  history <- ALL_DATA[seq_len(last_known), ]
  
  # Equity-only forecast using 15 lags
  FORECASTS$AR15[i] <- AR_ONE_STEP(history$ES, p = 15)
  
  # Cross-market forecast using 15 lags
  fitted_var15 <- VAR(
    history[, c("ES", "CL", "GC")],
    p = 15,
    type = "const"
  )
  
  FORECASTS$VAR15[i] <- as.numeric(
    predict(fitted_var15, n.ahead = 1)$fcst$ES[1, "fcst"]
  )
  
  if (i %% 100 == 0) {
    message("Completed ", i, " of ", n_test, " forecasts")
  }
}

forecast_models <- c("AR", "VAR", "AR15", "VAR15", "Naive")

stopifnot(
  all(is.finite(as.matrix(FORECASTS[, forecast_models])))
)

ACCURACY <- do.call(
  rbind,
  lapply(forecast_models, function(model) {
    
    errors <- FORECASTS$actual - FORECASTS[[model]]
    
    data.frame(
      model = model,
      MSE = mean(errors^2),
      RMSE = sqrt(mean(errors^2)),
      MAE = mean(abs(errors))
    )
  })
)

ACCURACY

# Create storage for the two additional models
FORECASTS$AR15 <- NA_real_
FORECASTS$VAR15 <- NA_real_

# Generate their forecasts for every test date
for (i in seq_len(n_test)) {
  
  last_known <- n_initial + i - 1
  history <- ALL_DATA[seq_len(last_known), ]
  
  FORECASTS$AR15[i] <- AR_ONE_STEP(history$ES, p = 15)
  
  fitted_var15 <- VAR(
    history[, c("ES", "CL", "GC")],
    p = 15,
    type = "const"
  )
  
  FORECASTS$VAR15[i] <- as.numeric(
    predict(fitted_var15, n.ahead = 1)$fcst$ES[1, "fcst"]
  )
  
  if (i %% 100 == 0) {
    message("Completed ", i, " of ", n_test, " forecasts")
  }
}

# Confirm that the columns exist and contain finite forecasts
forecast_models <- c("AR", "VAR", "AR15", "VAR15", "Naive")

stopifnot(all(forecast_models %in% names(FORECASTS)))

stopifnot(
  all(is.finite(as.matrix(FORECASTS[, forecast_models])))
)

# Recalculate accuracy
ACCURACY <- do.call(
  rbind,
  lapply(forecast_models, function(model) {
    
    errors <- FORECASTS$actual - FORECASTS[[model]]
    
    data.frame(
      model = model,
      MSE = mean(errors^2),
      RMSE = sqrt(mean(errors^2)),
      MAE = mean(abs(errors))
    )
  })
)

ACCURACY

# Storage for the four differenced specifications
diff_models <- c("AR_D4", "VAR_D4", "AR_D14", "VAR_D14")

for (model in diff_models) {
  FORECASTS[[model]] <- NA_real_
}

for (i in seq_len(n_test)) {
  
  # Information available before the forecast target
  last_known <- n_initial + i - 1
  history <- ALL_DATA[seq_len(last_known), ]
  
  # Changes calculated using only available history
  diff_history <- as.data.frame(
    lapply(history[, c("ES", "CL", "GC")], diff)
  )
  
  # Latest observed equity log variance
  last_es <- tail(history$ES, 1)
  
  for (p in c(4L, 14L)) {
    
    ar_name <- paste0("AR_D", p)
    var_name <- paste0("VAR_D", p)
    
    # Forecast the change, then recover the log variance level
    FORECASTS[[ar_name]][i] <- last_es +
      AR_ONE_STEP(diff_history$ES, p = p)
    
    diff_var_fit <- VAR(
      diff_history,
      p = p,
      type = "const"
    )
    
    predicted_change <- as.numeric(
      predict(diff_var_fit, n.ahead = 1)$fcst$ES[1, "fcst"]
    )
    
    FORECASTS[[var_name]][i] <- last_es + predicted_change
  }
  
  if (i %% 100 == 0) {
    message("Completed ", i, " of ", n_test, " forecasts")
  }
}

# Compare all models on the same dates and log variance target
forecast_models <- c(
  "AR", "VAR", "AR15", "VAR15",
  "AR_D4", "VAR_D4", "AR_D14", "VAR_D14",
  "Naive"
)

stopifnot(
  all(is.finite(as.matrix(FORECASTS[, forecast_models])))
)

ACCURACY <- do.call(
  rbind,
  lapply(forecast_models, function(model) {
    
    errors <- FORECASTS$actual - FORECASTS[[model]]
    
    data.frame(
      model = model,
      MSE = mean(errors^2),
      RMSE = sqrt(mean(errors^2)),
      MAE = mean(abs(errors))
    )
  })
)

ACCURACY

CW_TEST <- function(actual, ar_forecast, var_forecast) {
  
  ar_error <- actual - ar_forecast
  var_error <- actual - var_forecast
  
  cw_adjusted <- ar_error^2 - var_error^2 +
    (ar_forecast - var_forecast)^2
  
  # The intercept estimates the average adjusted difference
  mean_fit <- lm(cw_adjusted ~ 1)
  
  # Standard error allowing heteroskedasticity and autocorrelation
  hac_cov <- sandwich::NeweyWest(
    mean_fit,
    prewhite = FALSE,
    adjust = TRUE
  )
  
  hac_se <- sqrt(hac_cov[1, 1])
  
  statistic <- as.numeric(coef(mean_fit)[1]) / hac_se
  
  data.frame(
    mean_adjusted_difference = mean(cw_adjusted),
    CW_statistic = statistic,
    p_one_sided = pnorm(statistic, lower.tail = FALSE)
  )
}

# Compare each VAR against its matching equity-only benchmark
MODEL_PAIRS <- data.frame(
  comparison = c(
    "Levels: 5 lags",
    "Levels: 15 lags",
    "Differences: 4 lags",
    "Differences: 14 lags"
  ),
  ar = c("AR", "AR15", "AR_D4", "AR_D14"),
  var = c("VAR", "VAR15", "VAR_D4", "VAR_D14")
)

CW_RESULTS <- do.call(
  rbind,
  lapply(seq_len(nrow(MODEL_PAIRS)), function(j) {
    
    result <- CW_TEST(
      actual = FORECASTS$actual,
      ar_forecast = FORECASTS[[MODEL_PAIRS$ar[j]]],
      var_forecast = FORECASTS[[MODEL_PAIRS$var[j]]]
    )
    
    data.frame(
      comparison = MODEL_PAIRS$comparison[j],
      result
    )
  })
)

# Account for examining four comparisons
CW_RESULTS$p_Holm <- p.adjust(
  CW_RESULTS$p_one_sided,
  method = "holm"
)

CW_RESULTS

# Positive values favour VAR; negative values favour AR
loss_difference <- 
  (FORECASTS$actual - FORECASTS$AR)^2 -
  (FORECASTS$actual - FORECASTS$VAR)^2

plot(
  FORECASTS$date,
  cumsum(loss_difference),
  type = "l",
  xlab = "Forecast date",
  ylab = "Cumulative squared-error advantage of VAR",
  main = "VAR(5) compared with AR(5)"
)

abline(h = 0, col = "grey", lty = 2)

YEARLY_ACCURACY <- do.call(
  rbind,
  lapply(
    split(FORECASTS, format(FORECASTS$date, "%Y")),
    function(d) {
      
      ar_mse <- mean((d$actual - d$AR)^2)
      var_mse <- mean((d$actual - d$VAR)^2)
      
      data.frame(
        year = format(d$date[1], "%Y"),
        observations = nrow(d),
        AR_MSE = ar_mse,
        VAR_MSE = var_mse,
        VAR_gain_pct = 100 * (1 - var_mse / ar_mse)
      )
    }
  )
)

rownames(YEARLY_ACCURACY) <- NULL
YEARLY_ACCURACY
