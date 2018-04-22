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

# Matrix storage in parallel computing

Before discussing how matrices are diagonalized, I will first take a small detour and describe how matrices are represented in MPI based parallel applications. If you are already familiar with the concepts, feel free to skip ahead to the next [section]({{< ref "#scalapack" >}}).

Matrices with a large degree of nonzero elements, so called full or dense matrices, are usually represented in *block cyclic* format in MPI applications. This format is dictates how to distribute a matrix over a set of $N$ processors. Notice that other storage formats are typically preferable for sparse matrices, where the majority of matrix elements are zero, but I won't cover sparse matrices or algorithms designed specifically to diagonalize such matrices in this post.

Let's take a closer look at the block cyclic format with the help of following picture, which was taken from the excellent "Introduction to Parallel Computing" tutorial by Blaise Barney at the Lawrence Livermore National Laboratory.

![Matrix storage in parallel computing](https://computing.llnl.gov/tutorials/parallel_comp/images/distributions.gif)
**Figure 1.** Comparison of cyclic, block, and block cyclic format for representing matrices in parallel over multiple processors. The different colors represent different processors. Each colored segment represents a portion of the full matrix that resides in the local memory of a processor. Picture source: "Introduction to Parallel Computing" tutorial by Blaise Barney at the Lawrence Livermore National Laboratory.

In the cyclic decomposition of a matrix, each row, column or even adjacent element of the matrix is distributed onto different processors, wrapping over the set of processors repeatedly until all elements are exhausted. By constrast, in block decomposition, the matrix is divided into $N$, not necessarily evenly size, submatrices along the rows, columns, or combinations of both ("blocks"), and each submatrix is assigned to a different processor.

What are the pros and cons of these two distributions? Keep in mind that MPI was originally designed on a distributed memory [philosopy](https://en.wikipedia.org/wiki/Distributed_memory). In other words, each processor has its own private chunk of memory, and if a processor needs to access a portion of memory not in the local scope, it must request the data via communication. Note that the newer MPI-3 standard does allow direct shared memory programming (see e.g. [here](https://software.intel.com/en-us/articles/an-introduction-to-mpi-3-shared-memory-programming)), but it might not be available on all platforms. Taking these notions into account, we see that the cyclic distribution is superior for evenly distributing a matrix, but poor for matrix manipulations because a lot of communication is required since adjacent elements reside on different processors. The opposite holds true for block decomposition: linear algebra can be executed efficiently on contiguous submatrix blocks, but there might be load balancing issues e.g. if the matrix contains "sparse" regions. The block cyclic matrix distribution attempts to combine the best qualities of both representations by decomposing the matrix into blocks that are cyclically distributed among different processors.

The most efficient block cyclic layout is the two dimensional layout where the total $N$ processors are arranged into a rectangular grid $N = N\_{\mathrm{row}} \cdot N\_{\mathrm{col}}$ with $N\_{\mathrm{row}}$ rows and $N\_{\mathrm{col}}$ columns. This distribution has been visualized e.g. [here](https://www.hector.ac.uk/cse/distributedcse/reports/UniTBD/UniTBD/node18.html). The number of matrix rows and columns within a matrix block are controllable quantities, which are usually set to the same value making the blocks square. The block sizes are adjusted accordingly in case the matrix is not evenly divisible by the total number of processors. The two dimensional block cyclic layout has been adopted in the general purpose dense matrix linear algebra package [**ScaLAPACK**](https://www.netlib.org/scalapack/). This package is a reference library, i.e., it has been tested extensively on different platforms but the numerical performance has not been optimized for a specific architecture. Computing vendors provide their own tuned versions of the library that target specific hardware, e.g. Intel MKL or Cray LibSci, which should always be used for production calculations if available due to the significant speed advantages they offer.


# Parallel matrix diagonalization with ScaLAPACK {#scalapack}

Let's say we are given a matrix $\boldsymbol{\mathrm{A}}$ and our task is to diagonalize it. Matrix diagonalization is intimately linked with eigenvalue problems. Concretely, we can define matrix diagonalization as finding the solution to the following eigenvalue problem

$$ \boldsymbol{\mathrm{A}}\boldsymbol{\mathrm{X}}=\boldsymbol{\mathrm{X}}\boldsymbol{\mathrm{\Lambda}} $$

where $\boldsymbol{\mathrm{X}}$ is a matrix that contains the eigenvectors of $\boldsymbol{\mathrm{A}}$ and $\boldsymbol{\mathrm{\Lambda}}$ is the eigenvalue matrix. The eigenvalue matrix is the actual *diagonal* matrix we seek, because the eigenvalues of $\boldsymbol{\mathrm{A}}$ lie on its diagonal and zeroes everywhere else. The eigenvalue matrix can be computed with less work than the eigenvector matrix as we shall subsequently see. However, the eigenvectors are often useful in their own right in different applications.

Depending on the properties of $\boldsymbol{\mathrm{A}}$, there are a variety of [eigenvalue algorithms](https://en.wikipedia.org/wiki/Eigenvalue_algorithm) we could adopt to diagonalize the matrix. For the remainder of the post, I will assume that the matrix $\boldsymbol{\mathrm{A}}$ is a symmetric real matrix: $\boldsymbol{\mathrm{A}} = \boldsymbol{\mathrm{A}}^T$ (complex Hermitian case is fully analogous). Such matrices frequently appear in applications especially in the fields of computational chemistry and physics. The second assumption I will make is that the matrix $\boldsymbol{\mathrm{A}}$ is distributed in parallel over a set of processors in block cyclic distribution (see above).

The dense matrix linear algebra package ScaLAPACK offers [a number of algorithms](https://software.intel.com/en-us/mkl-developer-reference-c-scalapack-driver-routines) for diagonalizing for real symmetric matrices, which mainly differ in whether they are able to return all or just a subs.  I will futher assume that


If we set $\boldsymbol{\mathrm{A}}$ to be a $6 \times 6 $ matrix
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

the ScaLAPACK diagonalization process is comprised of the following steps

1. Reduction to tridiagonal form $\boldsymbol{\mathrm{T}}$ with Householder transformations $\boldsymbol{\mathrm{Q}}$
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
2. Solution of tridiagonal eigenvalue problem with [divide-and-conquer algorithm](https://en.wikipedia.org/wiki/Divide-and-conquer_eigenvalue_algorithm)
     $$ \boldsymbol{\mathrm{T}}\tilde{\boldsymbol{\mathrm{X}}} = \tilde{\boldsymbol{\mathrm{X}}}\boldsymbol{\mathrm{\Lambda}} $$
3. Backtransformation of eigenvectors
     $$ \boldsymbol{\mathrm{X}} = \boldsymbol{\mathrm{Q}}^T\tilde{\boldsymbol{\mathrm{X}}} $$



#