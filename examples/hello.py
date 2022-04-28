from cmdstanpy import CmdStanModel

model = CmdStanModel(exe_file='dist/bin/bernoulli')
model.sample(data='examples/bernoulli.data.json')
