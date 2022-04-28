library(cmdstanr)

# currently requires CmdStan to be installed
model <- cmdstan_model(exe_file="dist/bin/bernoulli")
data <- list(N=10, y=c(0, 1, 0, 0, 0, 0, 0, 0, 0, 1))
model$sample(data)
