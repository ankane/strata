# Strata

:mountain: The easy way to ship Stan models

[![Build Status](https://github.com/ankane/strata/workflows/build/badge.svg?branch=master)](https://github.com/ankane/strata/actions)

## Installation

Strata is a command line tool. To install, run:

```sh
pip install strata-cli
```

This will give you the `strata` command. You can also install it with [Homebrew](#homebrew).

## Getting Started

Package a model

```sh
strata bernoulli.stan
```

This creates a `dist` directory with:

- `bin` - Stan binaries
- `lib` - TBB libraries
- `licenses` - license files

You can also package multiple models

```sh
strata bernoulli.stan regression.stan
```

## Running Models

Run a model directly

```sh
dist/bin/bernoulli sample data ...
```

Or load it into [CmdStanPy](https://github.com/stan-dev/cmdstanpy)

```python
from cmdstanpy import CmdStanModel

model = CmdStanModel(exe_file='dist/bin/bernoulli')
```

[CmdStanR](https://github.com/stan-dev/cmdstanr) (not on CRAN yet)

```r
library(cmdstanr)

model <- cmdstan_model(exe_file="dist/bin/bernoulli")
```

Or [CmdStan.rb](https://github.com/ankane/cmdstan-ruby)

```ruby
require "cmdstan"

model = CmdStan::Model.new(exe_file: "dist/bin/bernoulli")
```

## Portability

- Linux: package on the oldest platform you support
- Mac: models run on macOS 10.14+ by default (set `MACOSX_DEPLOYMENT_TARGET` to override)
- Windows: not supported yet

## Cross-Compiling

Cross-compile for a different architecture (on the same OS)

```sh
strata --cross-compile ...
```

On Ubuntu, this requires:

```sh
sudo apt update
sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
```

## Reference

Specify the output directory

```sh
strata -o dist ...
```

Show build output

```sh
strata --debug ...
```

Create a static build (experimental, only working on Mac)

```sh
strata --static ...
```

## Homebrew

On Mac, you can use:

```sh
brew install ankane/brew/strata
```

## History

View the [changelog](https://github.com/ankane/strata/blob/master/CHANGELOG.md)

## Contributing

Everyone is encouraged to help improve this project. Here are a few ways you can help:

- [Report bugs](https://github.com/ankane/strata/issues)
- Fix bugs and [submit pull requests](https://github.com/ankane/strata/pulls)
- Write, clarify, or fix documentation
- Suggest or add new features

To get started with development:

```sh
git clone https://github.com/ankane/strata.git
cd strata
pip install -e .
```
