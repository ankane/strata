import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request

__version__ = '0.1.0'

# determine architecture
host_arch = platform.machine()
host_arm = 'arm' in host_arch or 'aarch' in host_arch

# when upgrading, check CLI11 and RapidJSON licenses
cmdstan_version = '2.30.0'
if host_arm and host_os == 'Linux':
    # only difference is stanc
    cmdstan_url = 'https://github.com/stan-dev/cmdstan/releases/download/v' + cmdstan_version + '/cmdstan-' + cmdstan_version + '-linux-arm64.tar.gz'
    cmdstan_checksum = '8ab1eaa83af100336e31fed1bcb854f30e7f775feb1274552fc706ed177969ef'
else:
    cmdstan_url = 'https://github.com/stan-dev/cmdstan/releases/download/v' + cmdstan_version + '/cmdstan-' + cmdstan_version + '.tar.gz'
    cmdstan_checksum = '009c2ea0043aa4a91c03ac78932e64f3cff4faa3e73413a2e0269d5be2d8de6c'


def parse_args():
    parser = argparse.ArgumentParser(usage='strata [FILES] [OPTIONS]')
    parser.add_argument('files', nargs='+', help='Stan files')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-o', '--output', default='dist', help='output directory')
    parser.add_argument('--overwrite', action='store_true', default=False, help='overwrite the output directory')
    parser.add_argument('--cross-compile', action='store_true', default=False, help='cross-compile')
    parser.add_argument('--debug', action='store_true', default=False, help='show build output')
    parser.add_argument('--clean', action='store_true', default=False, help=argparse.SUPPRESS)
    parser.add_argument('--static', action='store_true', default=False, help=argparse.SUPPRESS)
    return parser.parse_args()


def message(msg):
    print(msg, flush=True)


def stop(msg):
    message(msg)
    sys.exit(1)


def check_args(args):
    # check if all files exist
    for file in args.files:
        # TODO raise error if duplicate bin names
        if not Path(file).is_file():
            stop('File does not exist: ' + file)


def check_cross_compile():
    if host_arm:
        stop('Cannot cross-compile on ARM yet')

    if host_os == 'Linux':
        if not shutil.which('aarch64-linux-gnu-gcc') or not shutil.which('aarch64-linux-gnu-g++'):
            stop('Cross-compiler not found. Run:\nsudo apt update\nsudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu')


def check_output(file):
    if file.exists() and not args.overwrite:
        stop('File exists: ' + str(file) + '. Use --overwrite to overwrite.')


def run_command(cmd, env=None):
    stdout = None if args.debug else subprocess.PIPE
    stderr = None if args.debug else subprocess.STDOUT
    ret = subprocess.run([str(c) for c in cmd], stdout=stdout, stderr=stderr, universal_newlines=True, env=env)
    if ret.returncode != 0:
        if not args.debug:
            print(ret.stdout)
        stop('Command failed')


def download_archive(url, checksum):
    with tempfile.TemporaryDirectory() as tmpdir:
        file = Path(tmpdir).joinpath('file.tar.gz')
        # use str for Python 3.5
        urllib.request.urlretrieve(url, str(file))

        m = hashlib.sha256()
        with file.open('rb') as f:
            m.update(f.read())

        if m.hexdigest() != checksum:
            stop('Bad checksum: ' + m.hexdigest())

        # use tar instead of tarfile for safety
        run_command(['tar', 'xzf', file, '-C', workspace_dir])


def download_cmdstan():
    message('Downloading CmdStan...')
    download_archive(cmdstan_url, cmdstan_checksum)


def tbb_target(args):
    target = 'strata-tbb'
    if args.cross_compile:
        target += '-cc'
    if args.static:
        target += '-static'
    return target


def build_tbb():
    tbb_lib_dir.mkdir(exist_ok=True)

    tbb_args = [
        'tbb_root=' + str(tbb_dir),
        'cfg=release',
        '-C', tbb_lib_dir
    ]
    if args.cross_compile:
        if host_os == 'Darwin':
            tbb_args.append('arch=arm64')
            tbb_args.append('CONLY=gcc -target arm64-apple-macos11')
            tbb_args.append('CPLUS=g++ -target arm64-apple-macos11')
        else:
            tbb_args.append('arch=aarch64')
            tbb_args.append('CONLY=aarch64-linux-gnu-gcc')
            tbb_args.append('CPLUS=aarch64-linux-gnu-g++')

    if args.static:
        tbb_args.append('extra_inc=big_iron.inc')

    run_command(['make', '-f', tbb_dir.joinpath('build/Makefile.tbb')] + tbb_args, env=build_env)
    run_command(['make', '-f', tbb_dir.joinpath('build/Makefile.tbbmalloc'), 'malloc'] + tbb_args, env=build_env)
    run_command(['make', '-f', tbb_dir.joinpath('build/Makefile.tbbproxy'), 'tbbproxy'] + tbb_args, env=build_env)

    # reduce size
    for file in tbb_lib_dir.glob('*.so.2'):
        if args.cross_compile:
            run_command(['aarch64-linux-gnu-strip', '--strip-debug', file])
        else:
            run_command(['strip', '--strip-debug', file])


def requires_clean():
    # needs to be last file generated
    cmdstan_main = cmdstan_dir.joinpath('src/cmdstan/main.o')
    if cmdstan_main.exists():
        ret = subprocess.run(['file', str(cmdstan_main)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if ret.returncode != 0:
            return True

        # x86_64 on Mac, x86-64 on Linux
        cmdstan_arm = 'x86' not in ret.stdout
        return cmdstan_arm != target_arm

    return True


def clean_cmdstan():
    run_command(['make', 'clean-all', '-C', cmdstan_dir])


def cmdstan_args():
    build_args = ['-C', cmdstan_dir]

    # use precompiled TBB
    build_args.append('TBB_INC=' + str(tbb_dir.joinpath('include')))
    build_args.append('TBB_LIB=' + str(tbb_lib_dir))

    # only MPL2 or BSD code (see COPYING.README in Eigen)
    build_args.append('CXXFLAGS_EIGEN=-DEIGEN_MPL2_ONLY')

    # saves space
    build_args.append('PRECOMPILED_HEADERS=false')

    if host_os == 'Darwin':
        if args.static:
            tbb_ldflags = '-L$(TBB_LIB) -ltbb'
        else:
            # -L needed to prevent conflict with Homebrew tbb
            tbb_ldflags = '-L$(TBB_LIB) -Wl,-rpath,"@executable_path/../lib" -ltbb'
    else:
        if args.static:
            # TODO debug (cfg=debug above)
            # Assertion my_head failed on line 137 of file cmdstan-2.29.2/stan/lib/stan_math/lib/tbb_2020.3/src/tbb/observer_proxy.cpp
            # Detailed description: Attempt to remove an item from an empty list
            tbb_ldflags = ' '.join([str(x) for x in tbb_lib_dir.glob('*.a')])
        else:
            tbb_ldflags = '-Wl,-L,"$(TBB_LIB)" -Wl,-rpath,\'$$ORIGIN/../lib\' -Wl,--disable-new-dtags -ltbb'

    build_args.append('LDFLAGS_TBB=' + tbb_ldflags)

    if args.cross_compile:
        if host_os == 'Darwin':
            build_args.append('CC=gcc -target arm64-apple-macos11')
            build_args.append('CXX=g++ -target arm64-apple-macos11')
            build_args.append('OS=Darwin')
        else:
            build_args.append('CC=aarch64-linux-gnu-gcc')
            build_args.append('CXX=aarch64-linux-gnu-g++')
            build_args.append('OS=Linux')

    return build_args


def copy(src, dst):
    # use str for Python 3.5
    shutil.copy(str(src), str(dst))


def build_models():
    if requires_clean():
        clean_cmdstan()

    try:
        # for each stan file
        for i, file in enumerate(args.files):
            message('Building ' + file + '...')

            if i == 0:
                build_tbb()
                build_args = cmdstan_args()

            bin_name = Path(file).stem
            copy(file, cmdstan_dir.joinpath(bin_name + '.stan'))
            run_command(['make', bin_name] + build_args, env=build_env)
    finally:
        # not perfect, but try to clean after cross compilation
        # ideally could build object files in another directory
        if args.cross_compile:
            clean_cmdstan()


# TODO create in tmpdir and swap
def write_output():
    if output.exists() and args.overwrite:
        shutil.rmtree(str(output))

    # check again
    check_output(output)
    output.mkdir()

    bin_dir = output.joinpath('bin')
    bin_dir.mkdir()
    for file in args.files:
        bin_name = Path(file).stem
        copy(cmdstan_dir.joinpath(bin_name), bin_dir)

    if not args.static:
        lib_dir = output.joinpath('lib')
        lib_dir.mkdir()

        tbb_glob = '*.dylib' if host_os == 'Darwin' else '*.so*'
        for file in tbb_lib_dir.glob(tbb_glob):
            copy(file, lib_dir)

    licenses_dir = output.joinpath('licenses')
    licenses_dir.mkdir()
    copy(cmdstan_dir.joinpath('LICENSE'), licenses_dir.joinpath('cmdstan-license.txt'))
    copy(cmdstan_dir.joinpath('stan/LICENSE.md'), licenses_dir.joinpath('stan-license.txt'))
    copy(cmdstan_dir.joinpath('stan/lib/stan_math/LICENSE.md'), licenses_dir.joinpath('stan-math-license.txt'))
    copy(cmdstan_dir.joinpath('stan/lib/stan_math/lib/boost_1.78.0/LICENSE_1_0.txt'), licenses_dir.joinpath('boost-license.txt'))
    copy(cmdstan_dir.joinpath('stan/lib/stan_math/lib/sundials_6.1.1/LICENSE'), licenses_dir.joinpath('sundials-license.txt'))
    copy(cmdstan_dir.joinpath('stan/lib/stan_math/lib/sundials_6.1.1/NOTICE'), licenses_dir.joinpath('sundials-notice.txt'))
    copy(cmdstan_dir.joinpath('stan/lib/stan_math/lib/eigen_3.3.9/COPYING.MPL2'), licenses_dir.joinpath('eigen-mpl2-license.txt'))
    copy(cmdstan_dir.joinpath('stan/lib/stan_math/lib/eigen_3.3.9/COPYING.BSD'), licenses_dir.joinpath('eigen-bsd-license.txt'))
    copy(tbb_dir.joinpath('LICENSE'), licenses_dir.joinpath('tbb-license.txt'))
    copy(tbb_dir.joinpath('third-party-programs.txt'), licenses_dir.joinpath('tbb-third-party-programs.txt'))
    copy(package_dir.joinpath('licenses/cli11-license.txt'), licenses_dir.joinpath('cli11-license.txt'))
    copy(package_dir.joinpath('licenses/rapidjson-license.txt'), licenses_dir.joinpath('rapidjson-license.txt'))


# TODO move logic into main
def main():
    pass


args = parse_args()
check_args(args)

output = Path(args.output)
check_output(output)

host_os = platform.system()

if host_os == 'Windows':
    stop('Windows not supported yet')

if host_os == 'Darwin' and host_arm:
    stop('stanc3 not available for Mac ARM yet')

target_arm = host_arm
if args.cross_compile:
    target_arm = not host_arm
    check_cross_compile()

build_env = os.environ.copy()
if host_os == 'Darwin' and 'MACOSX_DEPLOYMENT_TARGET' not in build_env:
    build_env['MACOSX_DEPLOYMENT_TARGET'] = '11' if target_arm else '10.14'

package_dir = Path(__file__).parent
workspace_dir = Path.home().joinpath('.cmdstan')
cmdstan_dir = workspace_dir.joinpath('cmdstan-' + cmdstan_version)
tbb_dir = cmdstan_dir.joinpath('stan/lib/stan_math/lib/tbb_2020.3')
tbb_lib_dir = tbb_dir.parent.joinpath(tbb_target(args))

workspace_dir.mkdir(exist_ok=True)

if args.clean:
    if cmdstan_dir.exists():
        clean_cmdstan()

        if tbb_lib_dir.exists():
            shutil.rmtree(str(tbb_lib_dir))

if not cmdstan_dir.exists():
    download_cmdstan()

build_models()
write_output()
message('Success!')
