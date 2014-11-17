"""MSMBuilder: robust time series analysis for molecular dynamics and more.
"""

from __future__ import print_function, absolute_import

DOCLINES = __doc__.split("\n")

import os
import sys
import glob
import numpy as np
from numpy.distutils import system_info
from os.path import join as pjoin
from setuptools import setup, Extension, find_packages

sys.path.insert(0, '.')
from setupbase import write_version_py, build_ext, StaticLibrary, CompilerDetection

try:
    import Cython
    from Cython.Distutils import build_ext

    if Cython.__version__ < '0.18':
        raise ImportError()
except ImportError:
    print('Cython version 0.18 or later is required. Try "easy_install cython"')
    sys.exit(1)

# #########################
VERSION = '3.0.0-beta'
ISRELEASED = False
__version__ = VERSION
# #########################

CLASSIFIERS = """\
Intended Audience :: Science/Research
Intended Audience :: Developers
License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)
Programming Language :: C++
Programming Language :: Python
Development Status :: 4 - Beta
Topic :: Software Development
Topic :: Scientific/Engineering
Operating System :: POSIX
Operating System :: Unix
Operating System :: MacOS
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
"""

# Where to find extensions
MSMDIR = 'Mixtape/msm/'
HMMDIR = 'Mixtape/hmm/'
CLUSTERDIR = 'Mixtape/cluster/'

def get_lapack():
    from collections import defaultdict

    lapack_info = defaultdict(lambda: [])
    lapack_info.update(system_info.get_info('lapack'))
    if len(lapack_info) == 0:
        try:
            from scipy.linalg import _flapack

            lapack_info['extra_link_args'] = [_flapack.__file__]
            return lapack_info
        except ImportError:
            pass
        print('LAPACK libraries could not be located.', file=sys.stderr)
        sys.exit(1)
    return lapack_info


def write_spline_data():
    """Precompute spline coefficients and save them to data files that
    are #included in the remaining c source code. This is a little devious.
    """
    vmhmmdir = pjoin(HMMDIR, 'vonmises')
    import scipy.special
    import pyximport

    pyximport.install(setup_args={'include_dirs': [np.get_include()]})
    sys.path.insert(0, vmhmmdir)
    import buildspline

    del sys.path[0]
    n_points = 1024
    miny, maxy = 1e-5, 700
    y = np.logspace(np.log10(miny), np.log10(maxy), n_points)
    x = scipy.special.iv(1, y) / scipy.special.iv(0, y)

    # fit the inverse function
    derivs = buildspline.createNaturalSpline(x, np.log(y))
    if not os.path.exists(pjoin(vmhmmdir, 'data/inv_mbessel_x.dat')):
        np.savetxt(pjoin(vmhmmdir, 'data/inv_mbessel_x.dat'), x, newline=',\n')
    if not os.path.exists(pjoin(vmhmmdir, 'data/inv_mbessel_y.dat')):
        np.savetxt(pjoin(vmhmmdir, 'data/inv_mbessel_y.dat'), np.log(y),
                   newline=',\n')
    if not os.path.exists(pjoin(vmhmmdir, 'data/inv_mbessel_deriv.dat')):
        np.savetxt(pjoin(vmhmmdir, 'data/inv_mbessel_deriv.dat'), derivs,
                   newline=',\n')

compiler = CompilerDetection(False)
extensions = []
lapack_info = get_lapack()

extensions.append(
    Extension('mixtape.msm._markovstatemodel',
              sources=[pjoin(MSMDIR, '_markovstatemodel.pyx'),
                       pjoin(MSMDIR, 'src/transmat_mle_prinz.c')],
              include_dirs=[pjoin(MSMDIR, 'src'), np.get_include()]))

extensions.append(
    Extension('mixtape.msm._metzner_mcmc_fast',
              sources=[pjoin(MSMDIR, '_metzner_mcmc_fast.pyx'),
                       pjoin(MSMDIR, 'src/metzner_mcmc.c')],
              libraries=compiler.compiler_libraries_openmp,
              extra_compile_args=compiler.compiler_args_openmp,
              include_dirs=[pjoin(MSMDIR, 'src'), np.get_include()]))

extensions.append(
    Extension('mixtape.cluster._regularspatialc',
              sources=[pjoin(CLUSTERDIR, '_regularspatialc.pyx')],
              include_dirs=['Mixtape/src/f2py',
                            'Mixtape/src/blas',
                            np.get_include()]))

extensions.append(
    Extension('mixtape.cluster._kcentersc',
              sources=[pjoin(CLUSTERDIR, '_kcentersc.pyx')],
              include_dirs=['Mixtape/src/f2py',
                            'Mixtape/src/blas',
                            np.get_include()]))

extensions.append(
    Extension('mixtape.cluster._commonc',
              sources=[pjoin(CLUSTERDIR, '_commonc.pyx')],
              include_dirs=['Mixtape/src/f2py',
                            'Mixtape/src/blas',
                            np.get_include()]))

extensions.append(
    Extension('mixtape.hmm._ghmm',
              language='c++',
              sources=[pjoin(HMMDIR, 'wrappers/GaussianHMMCPUImpl.pyx')] +
                      glob.glob(pjoin(HMMDIR, 'src/*.c')) +
                      glob.glob(pjoin(HMMDIR, 'src/*.cpp')),
              libraries=compiler.compiler_libraries_openmp + lapack_info['libraries'],
              extra_compile_args=compiler.compiler_args_sse3 + compiler.compiler_args_openmp,
              extra_link_args=lapack_info['extra_link_args'] + compiler.compiler_libraries_openmp,
              include_dirs=[np.get_include(),
                            pjoin(HMMDIR, 'src/include/'),
                            pjoin(HMMDIR, 'src/')]))

extensions.append(
    Extension('mixtape.hmm._vmhmm',
              sources=[pjoin(HMMDIR, 'vonmises/vmhmm.c'),
                       pjoin(HMMDIR, 'vonmises/vmhmmwrap.pyx'),
                       pjoin(HMMDIR, 'vonmises/spleval.c'),
                       pjoin(HMMDIR, 'cephes/i0.c'),
                       pjoin(HMMDIR, 'cephes/chbevl.c')],
              libraries=['m'],
              include_dirs=[np.get_include(),
                            pjoin(HMMDIR, 'cephes')]))

write_version_py(VERSION, ISRELEASED, filename='Mixtape/version.py')
write_spline_data()
setup(name='mixtape',
      author='Robert McGibbon',
      author_email='rmcgibbo@gmail.com',
      description=DOCLINES[0],
      long_description="\n".join(DOCLINES[2:]),
      version=__version__,
      url='https://github.com/rmcgibbo/mixtape',
      platforms=['Linux', 'Mac OS-X', 'Unix'],
      classifiers=CLASSIFIERS.splitlines(),
      packages=['mixtape'] + ['mixtape.%s' % e for e in
                              find_packages('Mixtape')],
      package_dir={'mixtape': 'Mixtape'},
      scripts=['scripts/msmb'],
      zip_safe=False,
      ext_modules=extensions,
      cmdclass={'build_ext': build_ext})
