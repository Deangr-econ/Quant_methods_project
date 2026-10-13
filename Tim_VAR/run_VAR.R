# EBC4097: VAR analysis using the group's replacement dataset
# Extract the package; set the working directory to this folder.
# Once if needed: install.packages(c("vars", "urca"))
# Run: source("run_VAR.R")
# Original CSV is unchanged. Results from this script go to results_R/.

required <- c("vars", "urca")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop("Install first: ", paste(missing, collapse=", "))
input <- file.path("data", "group_data.csv")
if (!file.exists(input)) stop("Set the working directory to the extracted package folder.")
output <- "results_R"
dir.create(output, showWarnings=FALSE)
save_table <- function(x, file) write.csv(x, file.path(output,file),row.names=FALSE)
raw <- read.csv(input, stringsAsFactors=FALSE)
raw$date <- as.Date(raw$date)
markets <- c("ES","CL","GC","NG","C","TY")
data <- data.frame(date=raw$date)
for (v in head(markets,-1)) {
  stopifnot(all(raw[[paste0("rv5_",v)]] > 0),
    max(abs(raw[[paste0("log_rv5_",v)]]-log(raw[[paste0("rv5_",v)]]))) < 1e-10)
  data[[v]] <- raw[[paste0("log_rv5_",v)]]
}
data$TY <- raw$rv_yield_10
stopifnot(nrow(data)==3910L, !anyNA(data), !anyDuplicated(data$date),
  all(diff(data$date)>0), all(is.finite(as.matrix(data[markets]))),
  max(abs(raw$rv_yield_10-raw$abs_dyield_10^2)) < 1e-8,
  max(abs(tail(raw$rv_yield_10,-1)-(100*diff(raw$dgs10))^2)) < 1e-8)
cutoff <- as.Date("2023-07-12")
training <- data[data$date<=cutoff,]
stopifnot(nrow(training)==3127L,sum(data$date>cutoff)==783L)

# The file's Treasury proxy is used as supplied. Its first model lag is the
# previous retained date. Forecast origin: after all previous-date inputs are
# available. The additional-delay sensitivity below relaxes this assumption.
calendar_controls <- function(dates) {
  month <- as.integer(format(dates,"%m"))
  weekday <- as.integer(format(dates,"%u"))
  stopifnot(all(weekday %in% 1:5))
  out <- cbind(outer(month,2:12,"=="),outer(weekday,2:5,"=="))*1
  colnames(out) <- c(sprintf("month%02d",2:12),paste0("weekday",2:5))
  out
}
sets <- list(AR="ES", `Oil and gold`=c("ES","CL","GC"),
  `Gas and Treasury`=c("ES","NG","TY"),
  `All commodities`=c("ES","CL","GC","NG","C"), `Full VAR`=markets)

# Full-system lag selection on the initial training sample only.
selection <- vars::VARselect(training[markets], lag.max=20, type="const",
                             exogen=calendar_controls(training$date))
p_BIC <- as.integer(selection$selection["SC(n)"])
p_AIC <- as.integer(selection$selection["AIC(n)"])
stopifnot(p_BIC==4L,p_AIC==9L)
save_table(data.frame(p=1:20,AIC=selection$criteria["AIC(n)",],
  BIC=selection$criteria["SC(n)",]),"lag_selection.csv")

equity_design <- function(d,cols,p) {
  rows <- seq.int(p+1L,nrow(d))
  out <- data.frame(ES=d$ES[rows])
  for (j in seq_len(p)) for (v in cols) out[[paste0(v,".l",j)]] <- d[[v]][rows-j]
  cbind(out,calendar_controls(d$date[rows]))
}
equity_newdata <- function(d,target,cols,p) {
  out <- list()
  for(j in seq_len(p)) for(v in cols) out[[paste0(v,".l",j)]] <- d[[v]][nrow(d)-j+1L]
  cbind(as.data.frame(out),calendar_controls(target))
}
fit_model <- function(d,cols,p) {
  if(length(cols)==1L) return(lm(ES~.,data=equity_design(d,cols,p)))
  controls <- calendar_controls(d$date)
  model <- vars::VAR(d[cols],p=p,type="const",exogen=controls)
  model$call$exogen <- controls
  model
}
predict_ES <- function(model,d,target,cols,p) {
  if(length(cols)==1L) return(as.numeric(predict(model,equity_newdata(d,target,cols,p))))
  as.numeric(predict(model,n.ahead=1L,dumvar=calendar_controls(target))$fcst$ES[1,"fcst"])
}

# Expanding, one-step forecasts. Every forecast is issued before its target is
# added to the estimation history. The same 783 target dates are used throughout.
forecast_case <- function(d,p,model_sets,label,reconstruct_levels=FALSE) {
  targets <- which(d$date>cutoff)
  out <- data.frame(date=d$date[targets],actual=data$ES[match(d$date[targets],data$date)])
  for(nm in names(model_sets)) out[[nm]] <- NA_real_
  for(i in seq_along(targets)) {
    row <- targets[i]; history <- d[seq_len(row-1L),];target <- d$date[row]
    for(nm in names(model_sets)) {
      cols <- model_sets[[nm]]; model <- fit_model(history,cols,p)
      pred <- predict_ES(model,history,target,cols,p)
      if(reconstruct_levels) pred <- pred+data$ES[match(target,data$date)-1L]
      out[[nm]][i] <- pred
    }
    if(i %% 100L==0L) message(label,": ",i,"/",length(targets))
  }
  out$Persistence <- data$ES[match(out$date,data$date)-1L]
  stopifnot(nrow(out)==783L,all(is.finite(as.matrix(out[,-1]))))
  out
}
scores <- function(f,p,label) {
  ar_mse <- mean((f$actual-f$AR)^2)
  do.call(rbind,lapply(setdiff(names(f),c("date","actual")),function(nm) {
    e <- f$actual-f[[nm]]; mse <- mean(e^2)
    data.frame(case=label,model=nm,p=p,n=length(e),MSE=mse,RMSE=sqrt(mse),
               MAE=mean(abs(e)),gain_vs_AR_pct=100*(1-mse/ar_mse))
  }))
}
forecasts <- list(); all_scores <- list(); diagnostic_rows <- list(); ftest_rows <- list()
for(label in c("BIC","AIC")) {
  p <- if(label=="BIC") p_BIC else p_AIC
  f <- forecast_case(data,p,sets,label)
  forecasts[[label]] <- f
  save_table(f,paste0("forecasts_",label,".csv"))
  all_scores[[label]] <- scores(f,p,label)
  for(nm in names(sets)) {
    cols <- sets[[nm]]; model <- fit_model(training,cols,p)
    eq <- if(nm=="AR") model else model$varresult$ES
    e <- residuals(eq);X <- model.matrix(eq);T <- length(e);k <- ncol(X)
    if(nm=="AR") {
      b <- coef(eq)[paste0("ES.l",seq_len(p))]
      C <- matrix(0,p,p); C[1,] <- b
      if(p>1) C[2:p,1:(p-1)] <- diag(p-1)
      max_root <- max(Mod(eigen(C,only.values=TRUE)$values))
    } else max_root <- max(vars::roots(model))
    # Standard residual serial-correlation LM check, using 20 residual lags.
    h <- 20L; aux <- cbind(X[-seq_len(h),,drop=FALSE],embed(e,h+1L)[,-1,drop=FALSE])
    response <- tail(e,-h);res <- lm.fit(aux,response)$residuals
    R2 <- 1-sum(res^2)/sum((response-mean(response))^2)
    LM <- length(response)*R2
    ac <- as.numeric(acf(e,lag.max=20,plot=FALSE)$acf)
    diagnostic_rows[[paste(label,nm)]] <- data.frame(case=label,model=nm,p=p,n=T,
      parameters_per_equation=k,max_root=max_root,residual_acf1=ac[2],
      residual_acf5=ac[6],residual_acf20=ac[21],BG20=LM,BG20_p=pchisq(LM,20,lower.tail=FALSE))
    if(nm!="AR") {
      # Null: all non-equity lag coefficients in the equity equation equal zero.
      keep <- grepl("^ES\\.l[0-9]+$",colnames(X)) | !grepl("\\.l[0-9]+$",colnames(X))
      restricted <- lm.fit(X[,keep,drop=FALSE],model.response(model.frame(eq)))
      q <- sum(!keep); Fstat <- ((sum(restricted$residuals^2)-sum(e^2))/q)/(sum(e^2)/(T-k))
      ftest_rows[[paste(label,nm)]] <- data.frame(case=label,model=nm,p=p,F=Fstat,q=q,
        df_resid=T-k,p_value=pf(Fstat,q,T-k,lower.tail=FALSE))
    }
  }
}
accuracy <- do.call(rbind,all_scores)
save_table(accuracy,"accuracy.csv")
save_table(do.call(rbind,diagnostic_rows),"diagnostics.csv")
save_table(do.call(rbind,ftest_rows),"granger_tests.csv")

# First-difference sensitivity, motivated by mixed ADF and KPSS results.
difference_data <- data[-1,]
for(v in markets) difference_data[[v]] <- diff(data[[v]])
dif_training <- difference_data[difference_data$date<=cutoff,]
dif_selection <- vars::VARselect(dif_training[markets],lag.max=20,type="const",
                                 exogen=calendar_controls(dif_training$date))
p_difference <- as.integer(dif_selection$selection["SC(n)"])
dfcasts <- forecast_case(difference_data,p_difference,sets[c("AR","Full VAR")],
                         "First differences",reconstruct_levels=TRUE)
save_table(scores(dfcasts,p_difference,"Differences"),"differenced_sensitivity.csv")

# Additional Treasury delay, using a matched AR with the same initial row loss.
delayed <- data[-1,];delayed$TY <- head(data$TY,-1)
tf <- forecast_case(delayed,p_BIC,sets[c("AR","Gas and Treasury","Full VAR")],"Treasury delay")
save_table(scores(tf,p_BIC,"Treasury delay"),"treasury_timing_sensitivity.csv")

# Training-only stationarity and descriptive statistics.
st <- list();ds <- list();seasonal <- list()
for(v in markets) {
  x <- training[[v]]
  adf <- urca::ur.df(x,type="drift",lags=20,selectlags="Fixed")
  kp <- urca::ur.kpss(x,type="mu",use.lag=28)
  st[[v]] <- data.frame(variable=v,ADF=as.numeric(adf@teststat[1,"tau2"]),
    ADF_lags=20,ADF_5pct=-2.86,KPSS=as.numeric(kp@teststat),KPSS_lags=28,KPSS_5pct=.463)
  ac <- as.numeric(acf(x,lag.max=20,plot=FALSE)$acf)
  ds[[v]] <- data.frame(variable=v,n=length(x),mean=mean(x),std=sd(x),min=min(x),max=max(x),ACF1=ac[2],ACF20=ac[21])
  if(v!="TY") {
    level <- raw[[paste0("rv5_",v)]][raw$date<=cutoff]
    m <- as.integer(format(training$date,"%m"))
    means <- tapply(level,m,mean)
    seasonal[[v]] <- data.frame(variable=v,month=as.integer(names(means)),
                                mean_RV5=as.numeric(means),relative_to_overall=as.numeric(means)/mean(level))
  }
}
save_table(do.call(rbind,st),"stationarity.csv")
save_table(do.call(rbind,ds),"descriptive_statistics_training.csv")
save_table(do.call(rbind,seasonal),"seasonality_training.csv")

# Check core numerical results against the supplied independently computed tables.
reference_file <- file.path("results","accuracy.csv")
if(file.exists(reference_file)) {
  reference <- read.csv(reference_file,stringsAsFactors=FALSE)
  comparison <- merge(reference,accuracy,by=c("case","model","p","n"),suffixes=c("_reference","_R"))
  stopifnot(nrow(comparison)==12L)
  max_error <- max(abs(comparison$MSE_reference-comparison$MSE_R))
  if(max_error>1e-7) stop("R/Python MSE comparison exceeds tolerance: ",max_error)
  message("R/Python MSE comparison passed: max difference = ",max_error)
}
print(accuracy,row.names=FALSE)
writeLines(capture.output(sessionInfo()),file.path(output,"R_session_info.txt"))
cat("Done. Results written to ",normalizePath(output),"\n",sep="")
