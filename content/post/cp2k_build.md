+++
tags = ["CP2K"]
categories = ["computational chemistry"]
archives = ["2017-04"]
date = "2017-04-26"
title = "Building CP2K on a Cray XC40"
keywords = [""]
autoThumbnailImage = "false"
thumbnailImagePosition = "top"
thumbnailImage =  "false"
metaAlignment = "center"
slug = "cp2k-build-cray-xc40"

+++

Compiling a [CP2K](https://www.cp2k.org/) binary -- the massively parallel, open-source quantum chemistry and solid state physics program written in Fortran 2003 -- can be a daunting task if you've never built a large project using [maketools](https://en.wikipedia.org/wiki/Make_(software)). This post aims to demystify the build process by showcasing a full CP2K build on a Cray XC40 supercomputer (codename [*Sisu*](https://research.csc.fi/sisu-supercomputer)) including dependencies.
<!--more-->

The CP2K installation process can be divided into four parts: [compiling dependencies]({{< ref "#build-dependency" >}}), [compiling the binary]({{< ref "#build-binary" >}}), checking that it works (= [regression testing]({{< ref "#test-binary" >}})), and benchmarking the performance of the binary. Several versions of the CP2K binary can be built using different parallelization strategies and combinations of optimization and debugging flags. In this post, I will focus on the first three steps of the installation process. I will devote a separate post for exploring the effects of different optimization flags/options, although I will build (some of the) binary variants in this post.

> This post was [last edited]({{< ref "#libxsmm" >}}) on August 28, 2018 after its original publish date on April 26, 2017.

<!-- toc -->

# Building the dependencies {#build-dependency}
## Mandatory dependencies

A number of mandatory prerequisites are needed to build CP2K. An up-to-date list can be found in the official [installation instructions](https://sourceforge.net/p/cp2k/code/HEAD/tree/trunk/cp2k/INSTALL). These include the obvious Fortran/C compilers and other build tools (make and Python) as well as the numerical libraries [BLAS](https://en.wikipedia.org/wiki/Basic_Linear_Algebra_Subprograms) and [LAPACK](https://en.wikipedia.org/wiki/LAPACK) for performing linear algebra operations. To build an [MPI](https://en.wikipedia.org/wiki/Message_Passing_Interface) parallelized binary (highly recommended!), you will also need a working MPI installation and a parallel version of the mathematical libraries (ScaLAPACK).

Most of the above dependencies are either directly available in most Linux distributions or they can be easily installed from official repositories using the distribution's package manager (*e.g.* `pacman` or `apt-get`). You should always use tuned vendor-provided libraries to maximize performance if one is available for your platform (*e.g.* use MKL on Intel machines instead of the reference Netlib BLAS/LAPACK library). These libraries should already be available when building on a hosted HPC machine but will require manual installation otherwise. A good source for help in building these dependencies can be found in the installation scripts of the CP2K [toolchain](https://sourceforge.net/p/cp2k/code/HEAD/tree/trunk/cp2k/tools/toolchain/). In fact, you can perform a complete installation of all dependencies with the toolchain, but here I will be manually installing only those dependencies that I need.

I will use the Cray Compilation Environment (CCE) with GNU compilers, Libsci for the (Sca)LAPACK/BLAS math libraries, and cray-mpich for MPI. These can simply be loaded as modules

{{< codeblock lang="bash" >}}

nholmber@sisu-login4 ~/ >>> module switch PrgEnv-cray PrgEnv-gnu
nholmber@sisu-login4 ~/ >>> module load cray-libsci && module load cray-mpich
nholmber@sisu-login4 ~/ >>> module list
Currently Loaded Modulefiles:
  1) modules/3.2.10.5                      14) ugni/6.0-1.0502.10863.8.29.ari
  2) eswrap/1.3.3-1.020200.1278.0          15) pmi/5.0.11
  3) switch/1.0-1.0502.60522.1.61.ari      16) dmapp/7.0.1-1.0502.11080.8.76.ari
  4) slurm                                 17) gni-headers/4.0-1.0502.10859.7.8.ari
  5) gcc/6.2.0                             18) xpmem/0.1-2.0502.64982.5.3.ari
  6) craype-haswell                        19) job/1.5.5-0.1_2.0502.61936.2.32.ari
  7) craype-network-aries                  20) dvs/2.5_0.9.0-1.0502.2188.1.116.ari
  8) craype/2.5.9                          21) alps/5.2.4-2.0502.9822.32.1.ari
  9) cray-mpich/7.5.1                      22) rca/1.0.0-2.0502.60530.1.62.ari
 10) totalview-support/1.2.0.10            23) atp/2.0.5
 11) totalview/2016.04.08                  24) PrgEnv-gnu/5.2.82
 12) cray-libsci/16.11.1
 13) udreg/2.3.2-1.0502.10518.2.17.ari

{{< /codeblock >}}

## Optional dependencies

In addition to the mandatory prerequisites listed in the previous section, a number of optional libraries can be linked to CP2K to extended its features and to improve its performance. I will be using the following libraries

* FFTW3 (improved FFT performance)
* libxsmm (improved matrix multiplication performance for small matrices)
* libgrid (improved performance for collocation/integration routines)
* ELPA (improved performance for matrix diagonalizations)
* libint (enables Hartree-Fock (HF) and post-HF calculations)
* libxc (provides a greater number of exchange-correlation functionals)

I will not build the FFTW3 library as it is available as a module (`module load fftw`, version 3.3.4.11) on my machine. For the other libraries, I will use the following settings to compile them unless otherwise specified

{{< codeblock lang="bash" >}}

export CC=cc
export FC=ftn
export CXX=CC
export CFLAGS="-O3 -ftree-vectorize -g -fno-omit-frame-pointer -march=haswell -mtune=haswell -ffast-math"
export FCFLAGS="-O3 -ftree-vectorize -g -fno-omit-frame-pointer -march=haswell -mtune=haswell -ffast-math"
export CXXFLAGS="-O3 -ftree-vectorize -g -fno-omit-frame-pointer -march=haswell -mtune=haswell -ffast-math"
export pkg_install_dir="/homeappl/home/nholmber/appl_sisu/lib/${libname}-${libver}"

{{< /codeblock >}}

where `${libname}` and `${libver}` are the name and version, respectively, of the library being built.

Each of these libraries is built using the standard maketools process -- `configure,` `make` and `make install` (see *e.g.* this [post](https://robots.thoughtbot.com/the-magic-behind-configure-make-make-install) if you are unfamiliar with the concept). The CCE automatically sets a number of compiler flags, for example, to link the Libsci math libraries. These features can be leveraged by using the Cray wrappers for all compilers (using `ftn` instead of `gfortran`). The CCE thus simplifies the configuration process somewhat but the key principles remain the same. Please refer to the toolchain for complete configuration scripts. I will use the same library versions that are used in the toolchain. The compute nodes on *Sisu* use Haswell processors which is why I've set the flags `-march=haswell -mtune=haswell -mavx2`.

### libxc

[Libxc](http://octopus-code.org/wiki/Libxc) is a library of exchange-correlation functionals for density functional theory calculations. It provides functionals ranging from LDA all the way to meta hybrid functionals. I will compile version `3.0` of the library. The list of functionals in this release can be found [here](http://octopus-code.org/wiki/Libxc_3.0_functionals). For instructions on how to use libxc functionals in CP2K, take a look at the corresponding [regtests](https://sourceforge.net/p/cp2k/code/HEAD/tree/trunk/cp2k/tests/QS/regtest-libxc/). Note that not all libxc functionals are supported by CP2K. The compilation proceeds as follows

{{< codeblock lang="bash" >}}
curl -O https://www.cp2k.org/static/downloads/libxc-3.0.0.tar.gz
tar -xvzf libxc-3.0.0.tar.gz
cd libxc-3.0.0
./configure --prefix="${pkg_install_dir}" --libdir="${pkg_install_dir}/lib" > configure.log 2>&1 &
make -j 4 > make.log 2>&1 &
make install > install.log 2>&1 &

{{< /codeblock >}}

### libint

[Libint](https://github.com/evaleev/libint) is a library for computing four center electron repulsion integrals. These integrals are needed for Hartree-Fock (hybrid exchange-correlation functionals) and other higher level (MP2, RPA) calculations. CP2K is compatible only with the first version of the library which have a minor release number of `=> 1.1.4` (libraries from the next major version `2.x.y` **wont** work). I will use version `1.1.6`, which is again the toolchain default.

To successfully compile libint, I had to remove the `-g -fno-omit-frame-pointer` flags from `CXXFLAGS`. I will compile libint to support angular momenta up to h-functions for energies (configure flag `--with-libint-max-am=5`) and g-functions for derivatives (`--with-libderiv-max-am1=4`)

{{< codeblock lang="bash" >}}
curl -O https://www.cp2k.org/static/downloads/libint-1.1.6.tar.gz
tar -xvzf libint-1.1.6.tar.gz
cd libint-1.1.6
./configure --prefix=${pkg_install_dir} \
            --with-libint-max-am=5 \
            --with-libderiv-max-am1=4 \
            --with-cc="$CC $CFLAGS" \
            --with-cc-optflags="$CFLAGS" \
            --with-cxx="$CXX" \
            --with-cxx-optflags="$CXXFLAGS" > configure.log 2>&1 &
make -j 4 > make.log 2>&1 &
make install > install.log 2>&1 &
{{< /codeblock >}}

### libgrid

Due to the dual basis set nature of CP2K, one of the key operations in CP2K is the integration and collocation of Gaussian products (routines `calculate_rho_elec` and `integrate_v_rspace`), where the sparse matrix representation of the electron density (coefficients of Gaussian basis functions) is mapped to realspace multigrids and its reverse operation. The routines implementing these operations can be tuned for a specific architecture and packed into a library (libgrid) using auto generation tools which can be found in the folder `${cp2k_basedir}/tools/autotune_grid`. Please refer to the `README` therein for additional details.

Building libgrid is slightly more involved than the other libraries. After unpacking all of the data, I set the following options in `config.in`

{{< codeblock lang="bash" >}}
FC_comp="ftn -ffree-form"
FCFLAGS_OPT=" -O3 -march=haswell -mtune=haswell -ffast-math -funroll-loops -ftree-vectorize -fno-omit-frame-pointer -g"
FCFLAGS_NATIVE="-march=haswell -mtune=haswell"
{{< /codeblock >}}

I then generated the makefile with `./generate_makefile.sh` and compiled all code variants using `make -j 4 all_gen` (on a login node). Each binary was then timed on the compute nodes using 1 core (`aprun -n 1 make all_run`), which took several hours. It might be possible to run this step in parallel but I opted for the safe choice. The best code variants were then selected with `make gen_best > make_gen_best.log 2>&1 &` and packaged into a library with `make libgrid.a`.

### ELPA

[ELPA](https://elpa.mpcdf.mpg.de/) is an efficient numerical library for diagonalizing matrices in a block-cyclic data layout (ScaLAPACK format). The library provides optimized kernels tailored to specific architectures. By default, all supported kernels are installed. The performance of ELPA usually exceeds the performance of vendor-specific diagonalization libraries.

 In CP2K, ELPA can be linked in to replace all calls to the ScaLAPACK diagonalization routine (`cp_fm_syevd`). The performance benefits should be most apparent in simulations using a standard diagonalization based solver ([`&DIAGONALIZATION`](https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/DIAGONALIZATION.html)) or when using the [`&FULL_ALL`](https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/DFT/SCF/OT.html#PRECONDITIONER) preconditioner for OT. It should be noted that ELPA cannot be used for 'small' systems (size of input matrix relative to the number of processors). I will build both MPI only and hybrid MPI/OpenMP versions of the library (version `2016.05.004`). Compared to the other libraries, some additional flags have to be defined in the configure phase but otherwise the installation proceeds analogously

{{< codeblock lang="bash" >}}
export shared_flag=yes
export cray_ldflags="-dynamic"

curl -O https://www.cp2k.org/static/downloads/elpa-2016.05.004.tar.gz
tar -xvzf elpa-2016.05.004.tar.gz
cd elpa-2016.05.004

mkdir -p obj_no_thread; cd obj_no_thread
../configure  --prefix=${pkg_install_dir} \
              --libdir="${pkg_install_dir}/lib" \
              --enable-openmp=no \
              --enable-shared=$shared_flag \
              --enable-static=yes \
              FCFLAGS="${FCFLAGS} -ffree-line-length-none" \
              CFLAGS="${CFLAGS}" \
              CXXFLAGS="${CXXFLAGS}" \
              LDFLAGS="-Wl,--enable-new-dtags ${cray_ldflags}" \
              > configure.log 2>&1 &
make -j 4 >  make.log 2>&1 &
make install > install.log 2>&1 &

# Threaded version
mkdir -p obj_thread; cd obj_thread
../configure  --prefix=${pkg_install_dir} \
              --libdir="${pkg_install_dir}/lib" \
              --enable-openmp=yes \
              --enable-shared=$shared_flag \
              --enable-static=yes \
              FCFLAGS="${FCFLAGS} -ffree-line-length-none" \
              CFLAGS="${CFLAGS}" \
              CXXFLAGS="${CXXFLAGS}" \
              LDFLAGS="-Wl,--enable-new-dtags ${cray_ldflags}" \
              > configure.log 2>&1 &
make -j 4 >  make.log 2>&1 &
make install > install.log 2>&1 &

{{< /codeblock >}}

To check which kernels were installed, you can use the `print_kernels` binary available in the object directory (where make was invoked) as below, or inspect the library header file `elpa_kernel_constants.h` which was installed in the `include` folder of the library.

{{< codeblock lang="bash" >}}
nholmber@sisu-login4 ~/a/b/e/obj_no_thread >>> ./elpa2_print_kernels
 This program will give information on the ELPA2 kernels,
 which are available with this library and it will give
 information if (and how) the kernels can be choosen at
 runtime


  ELPA supports threads: no
 Information on ELPA2 real case:
 ===============================
  choice via environment variable: yes
  environment variable name      : REAL_ELPA_KERNEL

  Available real kernels are:
  AVX kernels are optimized for FMA (AVX2)
 REAL_ELPA_KERNEL_GENERIC
 REAL_ELPA_KERNEL_GENERIC_SIMPLE
 REAL_ELPA_KERNEL_SSE
 REAL_ELPA_KERNEL_SSE_BLOCK2
 REAL_ELPA_KERNEL_SSE_BLOCK4
 REAL_ELPA_KERNEL_SSE_BLOCK6
 REAL_ELPA_KERNEL_AVX_BLOCK2
 REAL_ELPA_KERNEL_AVX_BLOCK4
 REAL_ELPA_KERNEL_AVX_BLOCK6
 REAL_ELPA_KERNEL_AVX2_BLOCK2
 REAL_ELPA_KERNEL_AVX2_BLOCK4
 REAL_ELPA_KERNEL_AVX2_BLOCK6

  At the moment the following kernel would be choosen:
 REAL_ELPA_KERNEL_GENERIC


 Information on ELPA2 complex case:
 ===============================
  choice via environment variable: yes
  environment variable name      : COMPLEX_ELPA_KERNEL

  Available complex kernels are:
  AVX kernels are optimized for FMA (AVX2)
 COMPLEX_ELPA_KERNEL_GENERIC
 COMPLEX_ELPA_KERNEL_GENERIC_SIMPLE
 COMPLEX_ELPA_KERNEL_SSE
 COMPLEX_ELPA_KERNEL_SSE_BLOCK1
 COMPLEX_ELPA_KERNEL_SSE_BLOCK2
 COMPLEX_ELPA_KERNEL_AVX_BLOCK1
 COMPLEX_ELPA_KERNEL_AVX_BLOCK2
 COMPLEX_ELPA_KERNEL_AVX2_BLOCK1
 COMPLEX_ELPA_KERNEL_AVX2_BLOCK2

  At the moment the following kernel would be choosen:
 COMPLEX_ELPA_KERNEL_GENERIC
{{< /codeblock >}}


### libxsmm {#libxsmm}

[Libxsmm](https://github.com/hfp/libxsmm) is a specialized matrix multiplication library for small matrices targeting Intel architecture. It substitutes CP2K's own (optional) libsmm library (`${cp2k_basedir}/tools/build_libsmm`). Small matrix multiplications are a common operation in CP2K because Gaussian basis functions are used, see *e.g.* the DBCSR timing report at the end of a CP2K output file. The library features [just-in-time](https://en.wikipedia.org/wiki/Just-in-time_compilation) code generation and overall the installation process is very simple. As a slight caveat, I actually had to compile version `1.7.1` of the library on [*Taito*](https://research.csc.fi/taito-user-guide) -- a computer cluster which has similar Haswell nodes like its supercomputer sibling -- due to issues with the gcc compiler on *Sisu* (which nonetheless works with version `1.5.1`). Thanks to the CSC service desk for discovering the workaround!

I installed libxsmm using

{{< codeblock lang="bash" >}}
curl -O https://www.cp2k.org/static/downloads/libxsmm-1.7.1.tar.gz
cd libxsmm-1.7.1
make -j 4 CXX=CC CC=cc FC=gfortran AVX=2 OPT=3 PREFIX=${pkg_install_dir} > make.log 2>&
make CXX=CC CC=cc FC=gfortran AVX=2 OPT=3 PREFIX=${pkg_install_dir} install
{{< /codeblock >}}

>**Edit on August 28, 2018:** Thanks to the help of [@hfp](https://github.com/hfp), one of the developers behind libxsmm, I managed to track down the cause behind the compilation crash on Sisu. Turns out that the [binutils](https://www.gnu.org/software/binutils/) were outdated (2.23.1) on Sisu, while a newer 2.25 version was available on Taito. This issue can be bypassed by compiling the library with the extra flag `INTRINSICS=1`, see also instructions [here](https://github.com/hfp/libxsmm/wiki/Compatibility#cray).


# Building the CP2K binary  {#build-binary}

Compiling the CP2K binary is very similar to building the dependencies. A development version of CP2K can be downloaded with

`svn checkout http://svn.code.sf.net/p/cp2k/code/trunk .`

Alternatively, you can download a stable release version following [these instructions](https://www.cp2k.org/download). I will use the latest SVN development version in this post (`r17867` at the time of writing). Instead of configuring the installation with a separate script, the compilation flags and external libraries are defined in an arch file (`${cp2k_basedir}/arch/`). A number of example arch files are included in the directory for different architectures. You can find more examples in the [CP2K dashboard](https://dashboard.cp2k.org/) or by searching the [CP2K Google groups forum](https://groups.google.com/d/forum/cp2k).

I will use the following arch file templates to build MPI only (popt) and hybrid MPI/OpenMP (psmp) versions of CP2K


{{< tabbed-codeblock "Basic CP2K arch file for Sisu (Cray XC40)" >}}
<!-- tab popt -->
# Module environment
# module switch PrgEnv-cray PrgEnv-gnu
# module load cray-libsci && module load cray-mpich && module load fftw

# Library paths
LIBINT_LIB=/homeappl/home/nholmber/appl_sisu/lib/libint-1.1.6/lib
LIBINT_INC=/homeappl/home/nholmber/appl_sisu/lib/libint-1.1.6/include
LIBXC_LIB=/homeappl/home/nholmber/appl_sisu/lib/libxc-3.0.0/lib
LIBXC_INC=/homeappl/home/nholmber/appl_sisu/lib/libxc-3.0.0/include
LIBXSMM_LIB=/homeappl/home/nholmber/appl_sisu/lib/libxsmm-1.7.1/lib
LIBXSMM_INC=/homeappl/home/nholmber/appl_sisu/lib/libxsmm-1.7.1/include
ELPA_INCLUDE_DIR=/homeappl/home/nholmber/appl_sisu/lib/elpa-2016.05.004/include/elpa-2016.05.004/
ELPA_DIR=/homeappl/home/nholmber/appl_sisu/lib/elpa-2016.05.004/lib
LIBGRID_LIB=/homeappl/home/nholmber/appl_sisu/lib/libgrid/

# Build tools
CC       = cc
CPP      =
FC       = ftn
LD       = ftn
AR       = ar -r

# Flags and libraries
CPPFLAGS =

DFLAGS   = -D__BLACS -D__GFORTRAN -D__FFTW3 -D__parallel -D__SCALAPACK -D__LIBXSMM \
           -D__HAS_NO_SHARED_GLIBC -D__LIBINT -D__LIBXC -D__ELPA=201605 \
           -D__LIBINT_MAX_AM=6 -D__LIBDERIV_MAX_AM1=5 -D__HAS_LIBGRID

CFLAGS   = $(DFLAGS)

FCFLAGS  = $(DFLAGS) -O3 -march=haswell -mtune=haswell -mavx2 \
		   -funroll-loops -ffast-math -ftree-vectorize \
           -ffree-form -ffree-line-length-512 -I$(LIBINT_INC) -I$(LIBXC_INC) -I$(LIBXSMM_INC) \
           -I$(ELPA_INCLUDE_DIR)/modules -I$(ELPA_INCLUDE_DIR)/elpa

LDFLAGS  = $(FCFLAGS) -L$(ELPA_DIR)

LIBS     = -L$(LIBINT_LIB) -L$(LIBXC_LIB) -L$(LIBXSMM_LIB) -L$(LIBGRID_LIB)\
           -lxcf90 -lxc -lderiv -lint -lstdc++ -lfftw3 \
           -lxsmm -lxsmmext -lxsmmgen -lxsmmf -ldl -lelpa -lgrid
<!-- endtab -->
<!-- tab psmp -->
# Module environment
# module switch PrgEnv-cray PrgEnv-gnu
# module load cray-libsci && module load cray-mpich && module load fftw

# Library paths
LIBINT_LIB=/homeappl/home/nholmber/appl_sisu/lib/libint-1.1.6/lib
LIBINT_INC=/homeappl/home/nholmber/appl_sisu/lib/libint-1.1.6/include
LIBXC_LIB=/homeappl/home/nholmber/appl_sisu/lib/libxc-3.0.0/lib
LIBXC_INC=/homeappl/home/nholmber/appl_sisu/lib/libxc-3.0.0/include
LIBXSMM_LIB=/homeappl/home/nholmber/appl_sisu/lib/libxsmm-1.7.1/lib
LIBXSMM_INC=/homeappl/home/nholmber/appl_sisu/lib/libxsmm-1.7.1/include
ELPA_INCLUDE_DIR=/homeappl/home/nholmber/appl_sisu/lib/elpa-2016.05.004/include/elpa-2016.05.004/
ELPA_DIR=/homeappl/home/nholmber/appl_sisu/lib/elpa-2016.05.004/lib
LIBGRID_LIB=/homeappl/home/nholmber/appl_sisu/lib/libgrid/

# Build tools
CC       = cc
CPP      =
FC       = ftn
LD       = ftn
AR       = ar -r

# Flags and libraries
CPPFLAGS =

DFLAGS   = -D__BLACS -D__GFORTRAN -D__FFTW3 -D__parallel -D__SCALAPACK -D__LIBXSMM \
           -D__HAS_NO_SHARED_GLIBC -D__LIBINT -D__LIBXC -D__ELPA=201605 \
           -D__LIBINT_MAX_AM=6 -D__LIBDERIV_MAX_AM1=5 -D__HAS_LIBGRID

CFLAGS   = $(DFLAGS)

FCFLAGS  = $(DFLAGS) -fopenmp -O3 -march=haswell -mtune=haswell -mavx2 \
		   -funroll-loops -ffast-math -ftree-vectorize \
           -ffree-form -ffree-line-length-512 -I$(LIBINT_INC) -I$(LIBXC_INC) -I$(LIBXSMM_INC) \
           -I$(ELPA_INCLUDE_DIR)/modules -I$(ELPA_INCLUDE_DIR)/elpa

LDFLAGS  = $(FCFLAGS) -L$(ELPA_DIR)

LIBS     = -L$(LIBINT_LIB) -L$(LIBXC_LIB) -L$(LIBXSMM_LIB) -L$(LIBGRID_LIB)\
           -lxcf90 -lxc -lderiv -lint -lstdc++ -lfftw3 -lfftw3_threads \
           -lxsmm -lxsmmext -lxsmmgen -lxsmmf -ldl -lelpa_openmp -lgrid
<!-- endtab -->
{{< /tabbed-codeblock >}}

Above in the templates, we use `DFLAGS` to tell which external libraries should be included in CP2K and how they have been configured (refer to the [`INSTALL`](https://sourceforge.net/p/cp2k/code/HEAD/tree/trunk/cp2k/INSTALL) file). The appropriate include and library files, which we built [earlier]({{< ref "#build-dependency" >}}), are included with `FCLAGS`, `LDFLAGS` and `LIBS`. You'll notice that these 'basic' templates are already using quite aggressive optimization flags

`-march=haswell -mtune=haswell -mavx2 -funroll-loops -ffast-math -ftree-vectorize`

(refer to the [gcc manual](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) for more details regarding the flags), which I've found not to be an issue with GNU compilers.  In the psmp version, threaded versions of the ELPA, FFTW3 and libxsmm library are linked to CP2K. Notice that the values of `libint_max_am` and `libderiv_max_am` need to be 1 larger than during compilation of libint (you can verify the correct values from the libint library header files).

In addition to the basic installation, I will compile binaries with [fused multiply-add](https://en.wikipedia.org/wiki/Multiply%E2%80%93accumulate_operation#Fused_multiply.E2.80.93add) (FMA) and hugepages (larger virtual memory [pages](https://en.wikipedia.org/wiki/Page_(computer_memory))) support. These might lead to performance improvements in certain use-cases (more on this later in the separate benchmarking post). FMA instructions can be enabled with by adding `-mfma` to `FCFLAGS`. On Cray XC40, hugepages can be used by loading any of the available modules with different pagesizes (`module avail craype-hugepages`). I will use the `craype-hugepages-32M` module with a pagesize of 32M. The pagesize can be changed at runtime without recompiling the binary by loading a different module (see `man intro_hugepages`).

With the arch files sorted, CP2K can be installed with

{{< codeblock lang="bash" >}}
cd makefiles
make -j 8 ARCH=your_arch VERSION="popt psmp"  > make.log 2>&1 &
{{< /codeblock >}}

which installs binaries into `${cp2k_basedir}/exe/your_arch/`. If your installation fails study the make log file carefully, reread the [installation instructions](https://sourceforge.net/p/cp2k/code/HEAD/tree/trunk/cp2k/INSTALL), and/or seek help online (the Google groups forum is a good source of information!).

# Testing the CP2K binary {#test-binary}

Having built a CP2K binary, the next step is to verify that it produces correct results for known test cases called regtests. CP2K ships with nearly 3000 regtests which you can find in the `${cp2k_basedir}/tests/` directory. The idea of regression testing is to compare the output of the newly compiled binary against reference values. A test-dependent tolerance parameter determines how much the output can deviate from the reference value before it is considered incorrect. The SVN development version of CP2K is regularly tested on different architectures and the results are collected in the [dashboard](https://dashboard.cp2k.org/). If the dashboard regression testers report no errors (due to issues with latest patches) binaries built using common compilers and machines should pass all regtests. Certain optimization flags or compiler versions might however lead to incorrect regtest results. In such an event, it is worth rerunning the test with a binary compiled with a lower optimization level to try and pinpoint any issues (*e.g* `-O1`). Sometimes wrong test results can be safely ignored if the error is small compared to the tolerance, but the assessment has to be made case-by-case.

The easiest way to run the full regtest suite on a local machine is to use make based testing `make -j X ARCH=your_arch VERSION=your_version test`. On HPC machines with a batch job submission system, the regtest script

`${cp2k_basedir}/tools/regtesting/do_regtest`

should be copied for example to the `${cp2k_basedir}/regtesting` directory. Next, a configuration file suitable to the machine must be created for running the script. I've used the following file for testing the popt binaries

{{< codeblock  lang="bash" >}}
# Name of the Fortran compiler used
export FORT_C_NAME=ftn

# Name and path to the MPI Fortran compiler used
export MPI_F90=ftn

# Base directory of CP2K
dir_base=$PWD

# CP2K version: sopt (serial), popt (MPI), ssmp (OpenMP), psmp (MPI+OpenMP) or other (debug...)
cp2k_version=popt

# Arch
dir_triplet=sisu
export ARCH=${dir_triplet}

# CP2K directory in the base directory
cp2k_dir=../

# Number of MPI processes per task: should be 1 for serial or 2 for parallel runs
numprocs=2

# Number of threads per process: should be 2 or more for OpenMP runs otherwise 1
numthreads=1

# Maximum number of tasks (CPU cores assigned) for compilation and execution
# Set maxtasks greater than numprocs*numthreads or to a multiple of it
# Allocate all CPU cores for the regtest run
maxtasks=96
# or restrict their number
#maxtasks=8

# Turn YES to stop regression testing if there are no changes in the svn repository
emptycheck="NO"

# Turn YES if a memory leak checker is used
leakcheck="NO"

# Default error tolerance
default_err_tolerance="1.0E-14"

# *** how to execute an input file [ cp2k_prefix input cp2k_postfix ]
# Leave empty for serial, add path to mpirun for parallel execution
cp2k_run_prefix="aprun -n ${numprocs}"
# Uncomment for testing of hugepages binary and comment out the above
# cp2k_run_prefix="aprun -n ${numprocs} -m1000h"
cp2k_run_postfix=""
#

# Do not update or rebuild cp2k
nosvn="nosvn"
quick="quick"
nobuild="nobuild"

# Allow the config file to set the maximum allowed time. Useful for valgrind runs
job_max_time="900"

{{< /codeblock >}}

The regtest can then be started by executing `./do_regtest -c $your_conf` in an appropriate batch job submission script. You can find more information about regression testing [here](https://www.cp2k.org/dev:regtesting).

I've tabulated the regtest results below for the binaries I built in the [previous section]({{< ref "#build-binary" >}}). The results reveal no issues with the binaries.

| Optimization level     |  Version   | OK     |  NEW   |  WRONG |
|:---------------------- |:----------:|:------:|:------:|:------:|
| 'Basic'                | popt       |  2955  |  19    |  0     |
|                        | psmp       |  2955  |  19    |  0     |
|  FMA                   | popt       |  2955  |  19    |  0     |
|                        | psmp       |  2955  |  19    |  0     |
|  FMA + Hugepages       | popt       |  2955  |  19    |  0     |
|                        | psmp       |  2955  |  19    |  0     |