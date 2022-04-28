require "cmdstan"

model = CmdStan::Model.new(exe_file: "dist/bin/bernoulli")
data = {"N" => 10, "y" => [0, 1, 0, 0, 0, 0, 0, 0, 0, 1]}
model.sample(data: data, chains: 5)
