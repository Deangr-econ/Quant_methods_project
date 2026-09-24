# Run from the project root: Rscript scripts/download_data.R
# Uses FRED's public CSV exports, not the authenticated FRED API.
# Existing raw files are reused so a rerun preserves the research sample.

args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])
if (length(script) != 1L) stop("Run this file with Rscript.")
root <- dirname(dirname(normalizePath(script, mustWork = TRUE)))
raw_dir <- file.path(root, "datasets", "raw")
processed_dir <- file.path(root, "datasets", "processed")
dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(processed_dir, recursive = TRUE, showWarnings = FALSE)
options(timeout = 90)

start <- as.Date("2017-01-01")
end <- as.Date("2025-12-31")
series <- data.frame(
  id = c("SP500", "DGS10", "DGS2", "DGS5", "DCOILBRENTEU", "VIXCLS"),
  column = c("sp500", "treasury_10y_pct", "treasury_2y_pct",
             "treasury_5y_pct", "brent_usd_per_barrel", "vix"),
  provider = c("S&P Dow Jones Indices LLC", rep("Board of Governors of the Federal Reserve System", 3),
               "U.S. Energy Information Administration", "Cboe"),
  units = c("Index", rep("Percent", 3), "USD per barrel", "Index"),
  stringsAsFactors = FALSE
)

read_series <- function(path, id) {
  d <- read.csv(path, colClasses = "character", check.names = FALSE,
                na.strings = c("", ".", "NA"))
  if (ncol(d) != 2L || !identical(names(d)[2], id) ||
      !names(d)[1] %in% c("DATE", "observation_date")) {
    stop("Unexpected CSV structure for ", id, "; inspect ", path)
  }
  names(d) <- c("date", "value")
  d$date <- as.Date(d$date)
  if (anyNA(d$date) || anyDuplicated(d$date)) stop("Invalid/duplicate dates in ", id)
  numeric_value <- suppressWarnings(as.numeric(d$value))
  if (any(!is.na(d$value) & !is.finite(numeric_value))) stop("Invalid numeric values in ", id)
  d$value <- numeric_value
  d <- d[d$date >= start & d$date <= end, ]
  d <- d[order(d$date), ]
  observed <- d$date[!is.na(d$value)]
  if (length(observed) < 2000L || min(observed) > start + 10 || max(observed) < end - 10) {
    stop("Incomplete requested coverage for ", id,
         ". FRED SP500 has a moving ten-year history limit; keep the original snapshot.")
  }
  if (id %in% c("SP500", "DCOILBRENTEU", "VIXCLS") && any(d$value <= 0, na.rm = TRUE)) {
    stop("Nonpositive observation in ", id, "; investigate before using log returns.")
  }
  d
}

manifest_path <- file.path(root, "datasets", "manifest.csv")
previous <- if (file.exists(manifest_path)) read.csv(manifest_path, stringsAsFactors = FALSE) else NULL
parts <- list()
records <- list()
for (i in seq_len(nrow(series))) {
  s <- series[i, ]
  name <- paste0(s$id, "_2017_2025.csv")
  path <- file.path(raw_dir, name)
  url <- paste0("https://fred.stlouisfed.org/graph/fredgraph.csv?id=", s$id,
                "&cosd=", start, "&coed=", end)
  downloaded_at <- NA_character_
  if (!file.exists(path)) {
    message("Downloading ", s$id)
    temp <- tempfile(pattern = "fred-", tmpdir = raw_dir, fileext = ".csv")
    tryCatch({
      status <- download.file(url, temp, mode = "wb", method = "libcurl", quiet = TRUE)
      if (status != 0L) stop("Download failed for ", s$id)
      read_series(temp, s$id)
      if (!file.rename(temp, path)) stop("Could not save ", path)
    }, finally = { if (file.exists(temp)) unlink(temp) })
    downloaded_at <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  } else {
    message("Using saved copy of ", s$id)
  }
  checksum <- unname(tools::md5sum(path))
  if (is.na(downloaded_at) && !is.null(previous)) {
    match_row <- which(previous$series_id == s$id & previous$md5 == checksum)
    if (length(match_row) == 1L) downloaded_at <- previous$downloaded_at_utc[match_row]
  }
  d <- read_series(path, s$id)
  observed <- d$date[!is.na(d$value)]
  records[[i]] <- data.frame(
    series_id = s$id, column = s$column, provider = s$provider, units = s$units,
    source_page = paste0("https://fred.stlouisfed.org/series/", s$id), download_url = url,
    requested_start = as.character(start), requested_end = as.character(end),
    downloaded_at_utc = downloaded_at, raw_file = paste0("datasets/raw/", name),
    md5 = checksum, rows = nrow(d), nonmissing = sum(!is.na(d$value)),
    missing = sum(is.na(d$value)), first_observation = as.character(min(observed)),
    last_observation = as.character(max(observed)),
    minimum = min(d$value, na.rm = TRUE), maximum = max(d$value, na.rm = TRUE)
  )
  # Save metadata after each successful series, including partial download runs.
  write.csv(do.call(rbind, records), manifest_path, row.names = FALSE, na = "")
  names(d)[2] <- s$column
  parts[[i]] <- d
}

# Outer join preserves source-specific holidays and missing observations.
# These are levels, not returns or a ready-made forecasting information set.
panel <- Reduce(function(x, y) merge(x, y, by = "date", all = TRUE), parts)
panel <- panel[order(panel$date), ]
output <- file.path(processed_dir, "market_levels_2017_2025.csv")
write.csv(panel, output, row.names = FALSE, na = "")
message("Saved ", nrow(panel), " dates to ", output)
message("Source coverage and checksums: ", manifest_path)
