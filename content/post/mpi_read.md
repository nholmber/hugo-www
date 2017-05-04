+++
tags = ["CP2K", "MPI", "computational chemistry"]
categories = ["parallel programming"]
archives = ["2017-05"]
date = "2017-05-04"
title = "Parallelizing I/O operations with MPI: A case study with volumetric data"
keywords = ["MPI", "computational chemistry"]
autoThumbnailImage = "false"
thumbnailImagePosition = "top"
thumbnailImage =  "false"
metaAlignment = "center"
slug = "mpi-io-cube"

+++

Lately, parsing volumetric data from large (> 300 MB) text files has been a computational bottleneck in my simulations. Because I expect to be processing hundreds of these files, I decided to parallelize the parser routine by leveraging the [message passing interface](https://en.wikipedia.org/wiki/Message_Passing_Interface) (MPI). I will describe my first experience with MPI I/O in this post by going through the synthesis process of the parallelized parser routine. I will also examine the performance of the parallel parser.

<!--more-->

<!-- toc -->

# Introduction {#intro}

The first time I had to directly interact with MPI code was when I began implementing so-called [mixed constrained DFT features into CP2K](https://manual.cp2k.org/trunk/CP2K_INPUT/FORCE_EVAL/MIXED/MIXED_CDFT.html), which essentially boiled down to moving and shuffling data between multiple processor groups. Admittedly, this process mainly involved using pre-existing wrappers to MPI routines to achieve what I wanted and I had to create just a few wrappers of my own. The exact details are, however, not that important in this context. I consider a clearer understanding of what is happening during MPI parallel simulations as the greatest benefit of this implementation process. Up till then, the inner workings of MPI parallel codes were very much a black box for me because I had no prior hands-on experience with MPI and the topic was only briefly covered during my chemist's studies. Since then I've grown increasingly accustomed with MPI, although I've just scratched the surface of the capabilities of MPI, but to this date I have never used MPI for file I/O.

In this post, I will apply MPI I/O to parallelize a routine that reads three dimensional volumetric data from a Gaussian cube file. I won't be reproducing the complete code in full detail to keep this post as general as possible. Instead I will describe the routine and the computational problem it strives to solve in pseudocode that borrows elements from Python and Fortran. The full code has been integrated into the [development version of CP2K](https://github.com/cp2k/cp2k/blob/master/cp2k/src/pw/realspace_grid_cube.F#L353) for those that it interests.

Assume you have a function `f(x,y,z)` and that you know its values on a discrete, rectangular three dimensional grid. This grid could be very large so you've decided that each processor should hold only a small subset of values of the full function. In this example, we assume that the grid can be distributed onto the processors either in one or two dimensions, thus, each processor holds either full `yz` slabs (1D processor distribution) or `z` (2D) slices of the data. The values of the function can be stored into a Gaussian cube file by iterating through the grid in row-major order and adding a line break after every 6th function value or when the last value along the `z` axis is reached (for fixed `{x,y}`). Each function value is printed in scientific notation using the format code `E13.5`. An actual Gaussian cube file would contain additional header lines that precede the volumetric data but they are irrelevant in the current context. In pseudocode, the cube file printing routine can be expressed in serial (undistributed grid) mode as

{{< codeblock lang="python" >}}
# Determine bounds of data
lbound = lower_bounds(f(x,y,z))
ubound = upper_bounds(f(x,y,z))

# Output format: line break every 6th value
# or when last value along z-direction
# for this value of {i, j} is printed (6E13.5)
for i in range(lbound(1), ubound(1)):
    for j in range(lbound(2), ubound(2)):
    	write(output, format) f(i, j, :)
{{< /codeblock >}}

# Parsing volumetric data: moving from serial to parallel

For the remainder of this post, assume again that the 3D grid is distributed onto an arbitrary number of processors in a fixed layout. Given a cube file of function values which is commensurate with the 3D grid, our goal is to parse the file and to distribute the data to the correct processors as efficiently as possible. The simplest way to achieve this is to read the file only on the master MPI process. Specifically, the master rank processes the file by going through it in order one `z` slice at a time and then sends the data slices to their actual owner using point-to-point communication routines (either blocking or non-blocking). Remember that by earlier assumption the `z` slices are the smallest indivisible chunks of data, *i.e.*, data along this axis is never subdivided onto multiple processors for fixed values of `x` and `y`. The process of reading and communicating the data can be sequential (repeated individual reads followed by a communication step) or interleaved. I will consider only the former possibility and call this routine 'serial' because only the master process reads the file. This routine resembles the routine from the [Introduction section]({{< ref "#intro" >}}) which was used for writing the volumetric data into a cube file

{{< codeblock lang="python" >}}
# Determine bounds of data
lbound = lower_bounds(f(x,y,z))
ubound = upper_bounds(f(x,y,z))

# Get MPI rank of this process, the total number of processes,
# and the rank of the master process
my_rank = MPI_get_rank()
max_rank = MPI_max_rank()
master = MPI_master_rank()

# Get the sets of grid points that each process owns
grid_point_sets = get_grid_points()

# Parse data
for i in range(lbound(1), ubound(1)):
    for j in range(lbound(2), ubound(2)):
        if my_rank = master:
            # Read function values f(i, j, :)
            read(inputfile, format) buffer

        # Determine rank of target processes who owns the data
        for ip in range(1, max_rank):
            if (i, j) in grid_point_sets(ip):
                target = ip

        # Send/Receive data
        if my_rank = master and target != my_rank:
            MPI_send(data=buffer, target=target, source=master, ...)
        else:
            # Master owns data -> use explicit copy
            input_buffer = buffer
            # Type conversion
            f(i, j, :) = string_to_float(input_buffer)

        if my_rank = target and my_rank != master :
            MPI_recv(data=input_buffer, source=master, ...)
            f(i, j, :) = string_to_float(input_buffer)

{{< /codeblock >}}

An obvious simplification of the above routine involves removing the communication step by directly reading the appropriate sections of the cube file individually on every processor. Instead of associating multiple filehandles with the file, which would be the result if each process called an intrinsic file opening routine, the file can be opened in parallel using `MPI_File_open`. A bookkeeping scheme is required to ensure each process reads data only local to it. A simple `offset` parameter given in bytes relative to the start of the file is sufficient for this purpose. The value of `offset` is globally incremented after each `z` slice is parsed with the slice byte length (= the number of entries in the slice multiplied by their length + the number of line breaks, see above). The noncollective MPI routine `MPI_File_read_at` can then be employed to read in the data. The resulting routine dubbed 'noncollective' can be expressed in pseudocode as

{{< codeblock lang="python" >}}
# Determine bounds of data
lbound = lower_bounds(f(x,y,z))
ubound = upper_bounds(f(x,y,z))

# Get MPI rank of this process
my_rank = MPI_get_rank()

# Open file with MPI
MPI_File_open(filehandle, filename, communicator_handle, ...)

# Get the set of grid points this process owns
grid_point_sets = get_grid_points()
my_grid_points = grid_point_sets(my_rank)

# Calculate byte length of data z-slices
msglen = (ubound(3)-lbound(3)+1)*size_of_entry+num_linebreaks

# Initialize byte offset
BOF = 0

# Parse data
for i in range(lbound(1), ubound(1)):
    for j in range(lbound(2), ubound(2)):
        if (i, j) in my_grid_points:
            # Read function values f(i, j, :)
            MPI_File_read_at(filehandle, input_buffer, ...)
            # Type conversion
            f(i, j, :) = string_to_float(input_buffer)

        # Update byte offset
        BOF += msglen

{{< /codeblock >}}

The final routine I will consider in this post is a variant of the 'noncollective' routine, where the noncollective MPI file read is replaced by the collective routine `MPI_File_read_all`. Using this routine requires slightly more setup but it should perform better because collectively the routine sees the file as contiguous data. More information about these and other MPI I/O routines can be found online. These [**lecture notes**](http://wgropp.cs.illinois.edu/courses/cs598-s16/lectures/lecture32.pdf) by William Gropp, for example, discuss the differences between available MPI I/O routines.

The 'collective' routine, which I won't be writing in pseudocode, involves the following steps

1) Calculate byte offsets (as above) to all processor local `z` slices and store them in an array whose length equals the total number of slices

2) Create another array of equal length to store the byte lengths of each slice (constant, in this case)

3) Create a suitable MPI datatype for reading in the cube file in one read call (array of strings, with each array element corresponding to a slice)

4) Set a file view with the created MPI datatype

5) Read the file

# Performance analysis

I've compared the performance of the parallel routines against the serial reference on the following systems

* Local workstation: 4-core (+ 4 with HT) Intel Xeon E3-1230 V2 and 16 GB memory
* Sisu supercomputer: 2 × 12-core Intel Xeon E5-2690v3 and 64 GB memory (per computational node), dedicated parallel distributed filesystem (Lustre)

For the first benchmark, I will be using two small Gaussian cube files each consisting of 96 × 96 × 96 values. The cube files will be parsed as part of [a regression test](https://github.com/cp2k/cp2k/blob/master/cp2k/tests/QS/regtest-cdft-2/HeH-cdft-2.inp) of the CP2K quantum chemistry code and I will report timing data only for the parser routine `cube_to_pw`. I benchmarked all three routines discussed in this post by varying the number of MPI processes. The results are tabulated below.

**Table 1.** Time needed to parse a Gaussian cube as the function of the number of MPI processes with different parser routines on two different machines. The values are averages from parsing two files each consisting of 96 × 96 × 96 values.

| # MPI <br/> proc. | <br/> `Serial` | Local <br/> `Read_at` | <br/> `Read_all` | <br/> `Serial` | Sisu <br/>`Read_at` | <br/> `Read_all` |
|:----------------------- |:----------:|:------:|:------:|:------:|:------:|:------:|
| 1                       | 0.48       | 15.99  |  0.63  |  0.46  |  0.87  |  0.50  |
| 2                       | 0.54       |  8.42  |  0.25  |  0.47  |  0.44  |  0.26  |
| 4                       | 0.68       |  6.89  |  0.14  |  0.50  |  0.24  |  0.15  |
| 8                       | 1.49       | 13.89  |  0.12  |  0.53  |  0.13  |  0.08  |
| 12                      |  -         |  -     |  -     |  0.57  |  0.10  |  0.07  |
| 24                      |  -         |  -     |  -     |  0.68  |  0.07  |  0.05  |

On my local workstation, which does not have a dedicated parallel distributed filesystem, the noncollective (`MPI_Read_at`) parser routine is obviously very slow compared to the serial routine. By contrast, the collective (`MPI_Read_all`) routine performs significantly better than the serial version on both machines as the number of MPI processes is increased, resulting in a factor of 10 decrease in the time needed to process the Gaussian cube file. On Sisu, the noncollective routine is also faster than the serial parser but it is outperformed by the collective routine.

The tests above were conducted with cube files that are notably smaller than those I will be parsing in my computational workflow. For a more realistic benchmark, I will be processing cube files with 297 × 297 × 297 entries, focusing solely on the collective parallel and serial parser routines. These tests will only be run on Sisu. The results are presented in Table 2.


**Table 2.** Time needed to parse a Gaussian cube as the function of the number of MPI processes with different parser routines on Sisu. The values are averages from parsing four files each consisting of 297 × 297 × 297 values.


| # MPI processes         | `Serial`   | `MPI_Read_all`  |
|:----------------------- |:----------:|:--------------: |
| 48                      | 33.31      | 1.38            |
| 96                      | 60.55      | 0.69            |
| 192                     | 106.35     | 0.59            |

With larger cube files, the difference between the serial and parallel parser routines is even more apparent. The serial parser performs ever slower as the number of MPI processes is increased. The parallel routine scales linearly from 48 to 96 MPI processes, thereafter saturating once even more processes are utilized with scaling limited by the size of the cube file. Overall, the parallel parser is a fantastic two orders of magnitude faster than the serial routine with >96 MPI processes. Notice that I did not perform this benchmark with less than 48 MPI processes (or indeed just one) because the rest of the machinery within the quantum chemistry code that I am using scales well to 192 cores for this particular system.

# Conclusions

In this post, I parallelized a volumetric data parser with MPI I/O which lead to a significant performance boost for massively parallel simulations. My benchmarks clearly demonstrated the benefits of using MPI I/O for writing or reading large data sets in MPI parallel applications. The threshold for implementing I/O routines with MPI is low and requires just a moderate understanding of the message passing paradigm.