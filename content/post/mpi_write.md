+++
tags = ["CP2K", "MPI", "computational chemistry"]
categories = ["parallel programming"]
archives = ["2017-12"]
date = "2017-12-19"
title = "Parallelizing I/O operations with MPI: A case study with volumetric data. Part 2: Accurate MPI I/O timings and Cray DataWarp"
keywords = ["MPI", "computational chemistry", "DataWarp"]
autoThumbnailImage = "false"
thumbnailImagePosition = "top"
thumbnailImage =  "false"
metaAlignment = "center"
slug = "mpi-io-cube-pt2"

+++

In my previous [post]({{< ref "mpi_read.md" >}}), I discussed the benefits of using the message passing interface (MPI) to parse large data files in parallel over multiple processors. In today's post, I will continue exploring how I/O operations can be accelerated in MPI parallelized environments by implementing the corresponding writer routine to the problem that was described in my previous post. The focus of this post will, however, be  . I will also , which

<!--more-->

<!-- toc -->

# Implementing the parallel writer routine

To recap, our goal is to output the values of a function `f(x,y,z)` to disk in Gaussian cube file format. The values of this function are known on a discrete, rectangular three dimensional grid and each processor holds only a small subset of the total number of function values.

The task of writing a cube file in parallel is essentially identical to reading the data in parallel, which was discussed in depth in my previous [post]({{< ref "mpi_read.md" >}}). Here, I will therefore only be giving an outline of the parallelized writer routine. You can find the full code [here](https://github.com/cp2k/cp2k/blob/master/cp2k/src/pw/realspace_grid_cube.F#L623-L624) if you are interested.

- Open file in parallel (emulating file actions such as 'replace' with other MPI routines)
- Write header lines on master process
- Determine where each processor needs to write its data *i.e* determine byte offsets for the processor-dependent data slices
- Convert data to correct format (float -> string)
- Use calculated byte offsets as a file view
- Output data in parallel using collective MPI output routine
- Close file

# Supercomputing: traditional HDD vs SSD

Modern computers are nowadays typically equipped with both a hard disk drive (HDD) and a solid-state drive (SSD). The latter offers superior read/write performance and durability at the expense of higher investment cost and shorter data longevity (arguable given how often consumers replace their computer with a new one). To get the best of worlds, it is advantageous to use a SSD to store the computer's operating system and frequently used programs to improve load up times, while other, less accessed data such as images are stored on the HDD.

In the supercomputing world, SSDs are still relatively rare. The limited read/write longevity prevents replacing al. On Burst Buffer architechture

# Performance analysis: parallel vs serial

I've compared the performance of the parallel routines against the serial reference on the following systems

* Local workstation: 4-core (+ 4 with HT) Intel Xeon E3-1230 V2 and 16 GB memory
* Sisu supercomputer: 2 × 12-core Intel Xeon E5-2690v3 and 64 GB memory (per computational node), dedicated parallel distributed filesystem (Lustre)

For the first benchmark, I will be using two small Gaussian cube files each consisting of 96 × 96 × 96 values. The cube files will be parsed as part of [a regression test](https://github.com/cp2k/cp2k/blob/master/cp2k/tests/QS/regtest-cdft-2/HeH-cdft-2.inp) of the CP2K quantum chemistry code and I will report timing data only for the parser routine `cube_to_pw`. I benchmarked all three routines discussed in this post by varying the number of MPI processes. The results are tabulated below.


# Fine tuning MPI I/O performance
