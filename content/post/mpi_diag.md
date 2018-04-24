+++
tags = ["CP2K", "MPI", "computational chemistry", "high-performance computing", "linear algebra"]
categories = ["parallel programming"]
archives = ["2018-04"]
date = "2018-04-22"
title = "Matrix diagonalization in parallel computing: Benchmarking ELPA against ScaLAPACK"
keywords = ["MPI", "computational chemistry"]
autoThumbnailImage = "false"
thumbnailImagePosition = "top"
thumbnailImage =  "false"
metaAlignment = "center"
slug = "mpi-diagonalization"

+++


Matrix diagonalization is one of the most fundamental linear algebra operations with a wide range of applications in scientific and other computing. At the same time, it is also one of the most expensive operations with a formal [computational complexity](https://en.wikipedia.org/wiki/Computational_complexity_of_mathematical_operations) of a $\mathcal{O}(N^3)$, which could become a performance limiting factor in large systems. In this post, I will begin by briefly describing the canonical way of diagonalizing matrices in parallel to set the scene for today's main topic: tuning diagonalization performance. With the help of benchmark calculations, I will then demonstrate how clever mathematical library choices and parameter tuning can easily reduce the time needed for diagonalization by up to 50 %.

<!--more-->


It has been a hectic late winter--early spring for me as I have been gathering data for the last manuscript to be included in my PhD thesis, which has unfortunately meant that I haven't had time to write any new posts in quite a while, although I had a number of topics already pre-planned. After a feverish couple weeks of writing, I can finally see the finish line in sight and I expect to have the manuscript submission ready by early May. This has .

As mentioned above, this post will focus on matrix diagonalization in parallel computing and introduce a nifty library for drastically improving performance without requiring extensive code modifications to implement. I will briefly discuss the algorithms involved to give you insight into how the calculations are accelerated. This post concludes my three part miniseries on parallel programming using the message passing interface (MPI) paradigm, at least for the foreseeable future. You can find my previous posts related to MPI I/O [here]({{< ref "mpi_read.md" >}}) and [here]({{< ref "mpi_write.md" >}}).

PS. You might notice that some of the symbols and equations in this post have been typeset in $\LaTeX$-esque fashion (to see the proper rendering, you need to enable JavaScript <i class="fa fa-smile-o" aria-hidden="true"></i>). I followed the instructions [here](https://gohugo.io/content-management/formats/#mathjax-with-hugo) to enable [MathJax](http://docs.mathjax.org/en/latest/index.html) in Hugo for displaying mathematical expressions. Note that you might have to escape some characters you normally wouldn't to get an equation to render properly, e.g., subscripts need to be written as `B\_{11}` not `B_{11}`

<!-- toc -->

# Matrix storage in parallel computing {#intro}

Before discussing how matrices are diagonalized, I will first take a small detour and describe how matrices are represented in MPI based parallel applications. If you are already familiar with the concepts, feel free to skip ahead to the next [section]({{< ref "#scalapack" >}}).

Matrices with a large degree of nonzero elements, so called full or dense matrices, are usually represented in *block cyclic* format in MPI applications. This format is dictates how to distribute a matrix over a set of $N$ processors. Notice that other storage formats are typically preferable for sparse matrices, where the majority of matrix elements are zero, but I won't cover sparse matrices or algorithms designed specifically to diagonalize such matrices in this post.

Let's take a closer look at the block cyclic format with the help of following picture, which was taken from the excellent "Introduction to Parallel Computing" tutorial by Blaise Barney at the Lawrence Livermore National Laboratory.

![Matrix storage in parallel computing](https://computing.llnl.gov/tutorials/parallel_comp/images/distributions.gif)
**Figure 1.** Comparison of cyclic, block, and block cyclic format for representing matrices in parallel over multiple processors. The different colors represent different processors. Each colored segment represents a portion of the full matrix that resides in the local memory of a processor. Picture source: "Introduction to Parallel Computing" tutorial by Blaise Barney at the Lawrence Livermore National Laboratory.

In the cyclic decomposition of a matrix, each row, column or even adjacent element of the matrix is distributed onto different processors, wrapping over the set of processors repeatedly until all elements are exhausted. By constrast, in block decomposition, the matrix is divided into $N$, not necessarily evenly size, submatrices along the rows, columns, or combinations of both ("blocks"), and each submatrix is assigned to a different processor.

What are the pros and cons of these two distributions? Keep in mind that MPI was originally designed on a distributed memory [philosopy](https://en.wikipedia.org/wiki/Distributed_memory). In other words, each processor has its own private chunk of memory, and if a processor needs to access a portion of memory not in the local scope, it must request the data via communication. Note that the newer MPI-3 standard does allow direct shared memory programming (see e.g. [here](https://software.intel.com/en-us/articles/an-introduction-to-mpi-3-shared-memory-programming)), but it might not be available on all platforms. Taking these notions into account, we see that the cyclic distribution is superior for evenly distributing a matrix, but poor for matrix manipulations because a lot of communication is required since adjacent elements reside on different processors. The opposite holds true for block decomposition: linear algebra can be executed efficiently on contiguous submatrix blocks, but there might be load balancing issues e.g. if the matrix contains "sparse" regions. The block cyclic matrix distribution attempts to combine the best qualities of both representations by decomposing the matrix into blocks that are cyclically distributed among different processors.

The most efficient block cyclic layout is the two dimensional layout where the total $N$ processors are arranged into a rectangular grid $N = N\_{\mathrm{row}} \cdot N\_{\mathrm{col}}$ with $N\_{\mathrm{row}}$ rows and $N\_{\mathrm{col}}$ columns. This distribution has been visualized e.g. [here](https://www.hector.ac.uk/cse/distributedcse/reports/UniTBD/UniTBD/node18.html). The number of matrix rows and columns within a matrix block are controllable quantities, which are usually set to the same value making the blocks square. The block sizes are adjusted accordingly in case the matrix is not evenly divisible by the total number of processors. The two dimensional block cyclic layout has been adopted in the general purpose dense matrix linear algebra package [**ScaLAPACK**](https://www.netlib.org/scalapack/). This package is a reference library, i.e., it has been tested extensively on different platforms but the numerical performance has not been optimized for a specific architecture. Computing vendors provide their own tuned versions of the library that target specific hardware, e.g. Intel MKL or Cray LibSci, which should always be used for production calculations if available due to the significant speed advantages they offer.


# Parallel matrix diagonalization with ScaLAPACK and ELPA {#scalapack}

To recap, let's say we are given a dense matrix $\boldsymbol{\mathrm{A}}$ that is distributed in parallel using MPI over a set of $N$ processors in block cyclic distribution (see [above]({{< ref "#intro" >}}) if these concepts are unclear). Our task is to diagonalize $\boldsymbol{\mathrm{A}}$ and we would like to do it as efficiently as possible.

Matrix diagonalization is intimately linked with eigenvalue problems and the [eigendecomposition](https://en.wikipedia.org/wiki/Eigendecomposition_of_a_matrix) of a matrix. Concretely, we can define matrix diagonalization as finding the solution to the following eigenvalue problem

$$ \boldsymbol{\mathrm{A}}\boldsymbol{\mathrm{X}}=\boldsymbol{\mathrm{X}}\boldsymbol{\mathrm{\Lambda}} $$

where $\boldsymbol{\mathrm{X}}$ is a matrix that contains the eigenvectors of $\boldsymbol{\mathrm{A}}$ and $\boldsymbol{\mathrm{\Lambda}}$ is the eigenvalue matrix. The eigenvalue matrix contains the eigenvalues of $\boldsymbol{\mathrm{A}}$ on its diagonal and zeroes everywhere else. It therefore is the *actual* diagonal matrix we seek. As I shall subsequently show, computing the eigenvalue matrix requires less work than the eigenvector matrix. However, eigenvectors are often useful in their own right in different applications and typically both.

Depending on the properties of $\boldsymbol{\mathrm{A}}$, there are a variety of [eigenvalue algorithms](https://en.wikipedia.org/wiki/Eigenvalue_algorithm) we could adopt to diagonalize the matrix. For the remainder of the post, I will assume that the matrix $\boldsymbol{\mathrm{A}}$ is a symmetric real matrix (or, analogously, complex Hermitian): $\boldsymbol{\mathrm{A}} = \boldsymbol{\mathrm{A}}^T$ . Such matrices frequently appear in applications especially in the fields of computational chemistry and physics.

Dense matrix linear algebra packages that are based on ScaLAPACK offer [three different algorithms](https://software.intel.com/en-us/mkl-developer-reference-c-scalapack-driver-routines) for diagonalizing for real symmetric matrices, namely, the `p?syevd`, `p?syevx` and `p?syevr` methods where `?` accepts differents value depending on the matrix data type, e.g., `d` for double precision matrices. These algorithms not only different in the approach taken to diagonalize the matrix, but also whether they are suitable for calculating selected eigenvalues of the input matrix or just all.

Let's examine the `p?syevd` algorithm in more detail by going through the main steps of the algorithm. To this end, let $\boldsymbol{\mathrm{A}}$ be the following $6 \times 6 $ matrix
$$
 \boldsymbol{\mathrm{A}} =
 \begin{bmatrix}
  A\_{11} & A\_{12} & A\_{13} & A\_{14} & A\_{15} & A\_{16}  \\\\\
  A\_{21} & A\_{22} & A\_{23} & A\_{24} & A\_{25} & A\_{26}  \\\\\
  A\_{31} & A\_{32} & A\_{33} & A\_{34} & A\_{35} & A\_{36}  \\\\\
  A\_{41} & A\_{42} & A\_{43} & A\_{44} & A\_{45} & A\_{46}  \\\\\
  A\_{51} & A\_{52} & A\_{53} & A\_{54} & A\_{55} & A\_{56}  \\\\\
  A\_{61} & A\_{62} & A\_{63} & A\_{64} & A\_{65} & A\_{66}
 \end{bmatrix}
$$

The ScaLAPACK eigenvalue algorithm `p?syevd` is comprised of the following steps

1. Reduction to tridiagonal form $\boldsymbol{\mathrm{T}}$ with [Householder transformations](https://en.wikipedia.org/wiki/Householder_transformation#Tridiagonalization) $\boldsymbol{\mathrm{Q}}$
     $$
      \boldsymbol{\mathrm{T}} = \boldsymbol{\mathrm{Q}}\boldsymbol{\mathrm{A}}\boldsymbol{\mathrm{Q}}^T =
      \begin{bmatrix}
       A\_{11} & A\_{12} & 0       & \cdots  & \cdots  & 0        \\\\\
       A\_{21} & A\_{22} & A\_{23} & \ddots  & \ddots  & \vdots   \\\\\
        0      & A\_{32} & A\_{33} & A\_{34} & \ddots  & \vdots   \\\\\
       \vdots  & \ddots  & A\_{43} & A\_{44} & A\_{45} & 0        \\\\\
       \vdots  & \ddots  & \ddots  & A\_{54} & A\_{55} & A\_{56}  \\\\\
       0       & \cdots  & \cdots  & 0       & A\_{65} & A\_{66}
      \end{bmatrix}
     $$
2. Solution of tridiagonal eigenvalue problem with [divide-and-conquer (DQ) algorithm](https://en.wikipedia.org/wiki/Divide-and-conquer_eigenvalue_algorithm)
     $$ \boldsymbol{\mathrm{T}}\tilde{\boldsymbol{\mathrm{X}}} = \tilde{\boldsymbol{\mathrm{X}}}\boldsymbol{\mathrm{\Lambda}} $$
3. Backtransformation of eigenvectors
     $$ \boldsymbol{\mathrm{X}} = \boldsymbol{\mathrm{Q}}^T\tilde{\boldsymbol{\mathrm{X}}} $$

The `p?syevx` and `p?syevr` methods differ from `p?syevd` in the second step of algorithm: the former relies on bisection and inverse iteration, whereas the latter on the multiple relatively robust representations (MRRR) iteration. You can find more in-depth details details about these two algorithms e.g. in this [paper](https://dl.acm.org/citation.cfm?id=1644002). Significant performance differences between these different algorithms become apparent only when a subset of the eigenvalues are required, because `p?syevd` always returns the full set of eigenvalues. However, keeping in mind our ultimate goal of diagonalizing the input matrix, it is clear that all.   In the remained of this post, I will therefore exclusively discuss the DQ method based `p?syevd` algorithm.

An alternative approach to improve the performance of the DQ ScaLAPACK algorith would be to modify steps 1 and 3 of the algorithm, that is, the reduction to triagonal form and the backtransformation operation. This strategy is adopted in the [Eigenvalues SoLvers for Petaflop-Applications](https://elpa.mpcdf.mpg.de/) (ELPA) library. Specifically, the direct transformations to tridiagonal form are replaced by a two step process, where the matrix is first converted to [banded form](https://en.wikipedia.org/wiki/Band_matrix) (i.e. to a matrix with more than 1 sub- and superdiagonal), and the banded matrix is subsequently reduced to diagonal form. The backtransformation to a full matrix is modified in analogous fashion. This choice increases the fraction of matrix-matrix linear algebra operations performed during the transformations and minimizes the fraction of matrix-vector operations, which should lead to overall higher numerical performance in the diagonalization algorithm. An optional blocked QR decomposition can be leveraged for further speed improvements. A detailed description of the ELPA library is given in [this review article](dx.doi.org/10.1088/0953-8984/26/21/213201).

ELPA offers a generic Fortran kernel that should would across different architectures as well as a host of tuned kernels for modern CPUs that support e.g. AVX, AVX2, or AVX-512 instruction sets. Even a GPU kernel has recently been implemented. ELPA is compiled with the standard configure & make approach. The interface to the ELPA diagonalization routine is very similar to the equivalent ScaLAPACK routine, which makes it a relatively straightforward task to include ELPA as an optional dependency in applications that already leverage ScaLAPACK for dense matrix diagonalization.


# Benchmarking ELPA against ScaLAPACK

Matrix diagonalization performance in general depends on a variety of factors:

  * Size of matrix (application dependent)
  * Structure of matrix (application dependent)
  * Number of processors used for diagonalization (user tunable setting)
  * MPI block size for matrix (user tunable setting)
  * Diagonalization algorithm (user tunable setting if implementation allows it)

The first two factors are fixed for a given problem, while the latter three can be optimized at least to a degree by the user. In this section, I will compare the diagonalization performance of the ScaLAPACK `p?syevd` and ELPA algorithms. I will examine two square matrix sizes with $5888$ and $13034$ elements, respectively, and measure how the algorithms scale as the number of processors, $N$, is increased. The two methods will also be constrasted. The CP2K quantum chemistry software is used for running the benchmarks with each data point corresponding to the average diagonalization time obtained from two separate simulations each involving a total of 10 diagonalizations of the input matrix. The CP2K input files are based on these (1) and (2) input files that are distributed with the software. The benchmarks were run on a Cray XC40 supercomputer (["Sisu"](https://research.csc.fi/sisu-supercomputer)) where each computational node is comprised of two 12-core Intel Xeon E5-2690v3 processors and 64 GB DDR4 memory. The matrix block size is set to 64 in both row and column dimensions which facilitates gauging the impact of the optional QR decomposition step in the ELPA algorithm (the QR decomposition works only even sized matrices with block size $\ge 64$). The 2017.05 version of ELPA and the AVX2_BLOCK2 kernel are used throughout.

As a side note, CP2K limits the number of MPI processes used for diagonalization because prior benchmarks on a Cray XE6 machine have shown ScaLAPACK diagonalization performance to suffer when the matrix is parallelized on too many processes relative to the size of the matrix. The 'optimal' number of processes for diagonalization, $M$, is computed using the heuristic $M = (K+a*x-1)/(a*x)*a$, where $K$ is the size of the input matrix, and $a$ and $x$ are integers with default values $a=4$ and $x=60$. If $M \lt N$, the matrix is redistributed onto $M$ processors before diagonalizing it. With ELPA, redistribution of the input matrix is performed only in the event that the calculation would otherwise crash within the ELPA library due to overparallelization, which causes some processors to hold no actual matrix elements. In addition to the tests discussed above, I have also estimated the effects of the optimial number of CPUs heuristic with ScaLAPACK by either disabling the check or by using the default values.

