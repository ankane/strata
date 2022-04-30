import os
from pathlib import Path
import platform
import pytest
import re
import shutil
import subprocess
import tempfile


project_dir = Path(__file__).parent.parent


class TestStrata:
    def setup_method(self, test_method):
        self.tempdir = tempfile.TemporaryDirectory()
        shutil.copytree(str(project_dir.joinpath('examples')), str(Path(self.tempdir.name).joinpath('examples')))
        os.chdir(self.tempdir.name)

    def teardown_method(self, test_method):
        self.tempdir.cleanup()

    def test_works(self):
        self.run_strata(['examples/bernoulli.stan'])
        assert Path('dist/bin/bernoulli').exists()
        assert Path('dist/lib').exists()
        assert Path('dist/licenses/boost-license.txt').exists()
        output = self.run_program(['dist/bin/bernoulli', 'sample', 'data', 'file=examples/bernoulli.data.json'])
        assert 'Iteration: 2000 / 2000 [100%]' in output

    @pytest.mark.skipif(platform.system() != 'Darwin', reason='Requires Mac')
    def test_static(self):
        self.run_strata(['examples/bernoulli.stan', '--static'])
        assert Path('dist/bin/bernoulli').exists()
        assert not Path('dist/lib').exists()
        output = self.run_program(['dist/bin/bernoulli', 'sample', 'data', 'file=examples/bernoulli.data.json'])
        assert 'Iteration: 2000 / 2000 [100%]' in output

    def test_cross_compile(self):
        self.run_strata(['examples/bernoulli.stan', '--cross-compile'])
        assert 'x86' not in self.run_command(['file', 'dist/bin/bernoulli'])

    def test_exists(self):
        Path('dist').mkdir()
        output = self.run_strata(['examples/bernoulli.stan'], error=True)
        assert 'File exists: dist. Use --overwrite to overwrite.' in output

    def test_help(self):
        assert 'usage' in self.run_strata(['--help'])

    def test_version(self):
        assert re.search(r'\d+\.\d+\.\d+', self.run_strata(['--version']))

    def run_strata(self, cmd, **kwargs):
        return self.run_command(['python3', project_dir.joinpath('strata/__init__.py')] + cmd, **kwargs)

    def run_program(self, cmd):
        src = Path.home().joinpath('.cmdstan')
        dst = Path.home().joinpath('.cmdstan2')
        try:
            shutil.move(str(src), str(dst))
            return self.run_command(cmd)
        finally:
            if dst.exists():
                shutil.move(str(dst), str(src))

    def run_command(self, cmd, error=False):
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if error:
            assert ret.returncode != 0
        elif ret.returncode != 0:
            print(ret.stdout)
            raise RuntimeError('Command failed')
        return ret.stdout
