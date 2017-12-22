+++
tags = ["CP2K", "MPI", "computational chemistry", "high-performance computing"]
categories = ["parallel programming"]
archives = ["2017-12"]
date = "2017-12-22"
title = "Parallelizing I/O operations with MPI, Part 2: Performance tuning and Cray Burst Buffer"
keywords = ["MPI", "computational chemistry", "DataWarp", "SSD"]
autoThumbnailImage = "false"
thumbnailImagePosition = "top"
thumbnailImage =  "false"
metaAlignment = "center"
slug = "mpi-io-cube-pt2"

+++

In my previous [post]({{< ref "mpi_read.md" >}}), I discussed the benefits of using the message passing interface (MPI) to parse large data files in parallel over multiple processors. In today's post, I will demonstrate how MPI I/O operations can be further accelerated by introducing the concept of hints. The second topic I will discuss is the emergence of solid-state drives in high-performance computing systems to resolve I/O bottlenecks. These topics will be illustrated by benchmark calculations using a parallel writer routine that I will implement to the [task described previously]({{< ref "mpi_read.md" >}}).

<!--more-->

<!-- toc -->

# Implementing the parallel writer routine

To recap, our goal is to output the values of a function `f(x,y,z)` to disk in Gaussian cube file format. The values of this function are known on a discrete, rectangular three dimensional grid with each processor holding only a small subset of the total number of function values.

The task of writing a cube file in parallel is essentially identical to reading the data in parallel, which was discussed in depth in my previous [post]({{< ref "mpi_read.md" >}}). Here, I will therefore only be giving an outline of the parallelized writer routine. You can find the full code [here](https://github.com/cp2k/cp2k/blob/master/cp2k/src/pw/realspace_grid_cube.F#L623-L624) if you are interested.

- Open file in parallel (emulating file actions such as 'replace' with other MPI routines)
- Write header lines on master process
- Determine where each processor needs to write its data *i.e* determine byte offsets for the processor-dependent data slices
- Convert data to correct format (float to string)
- Use calculated byte offsets as a file view
- Output data in parallel using collective MPI write routine
- Close file

# High-performance computing: traditional HDD vs SSD

Modern computers are nowadays often equipped with both a hard disk drive (HDD) and a solid-state drive (SSD). The latter offers superior read/write performance and physical durability at the expense of higher cost and shorter data longevity (arguable given how often consumers replace their computer with a new one). To get the best of worlds, it is advantageous to use a SSD to store the computer's operating system and frequently used programs to improve load up times, while other, less accessed data such as images are stored on the HDD.

In the high-performance computing world, SSDs are still relatively rare. The limited read/write longevity of SSDs becomes a real issue for data-intensive computing centers, and it is unrealistic to transition from HDD-only systems to SSD-only systems despite the gain in I/O performance. The I/O performance of HDDs is actually quite impressive in a high-performance computing setting for large files because the files are split (striped) over many disks via the parallel file system. [NERSC, for example, reports a peak I/O performance of over 700 GB/s for their Cray XC40 supercomputer Cori](http://www.nersc.gov/users/computational-systems/cori/file-storage-and-i-o/). Noticeable slow downs are experienced when the system is under high I/O load or when data is accessed frequently in small chunks. This is where SSDs come into the picture, not as the final storage location of all computing data, but as a fast buffer drive intended to absorb peak I/O loads.

Cray has named their SSD architecture Burst Buffer which reflects its intended purpose. The Burst Buffer nodes can be utilized in a number of ways. In the simplest case, all temporary files that are created during a simulation but destroyed afterwards are written to and subsequently read from the SSDs. Permanent input or output data can also be read/written on the Burst Buffer nodes by staging in/out the files from the HDD parallel file system. In practice, an output file would first get written to the SSDs and then moved (staged out) to the HDDs when the allocated computing time runs out. If your simulation suffers from I/O bottlenecks this strategy might significantly reduce the run time of your code because the slow HDD I/O is disentangled from the actual computation phase.

The Burst Buffer nodes are controlled by the DataWarp software which determines *e.g.* in which operating mode the nodes are used and how many nodes the files are striped over. The software also integrates the Burst Buffers nodes with the workload manager and other parts of the computing environment. You can find more detailed information about the Burst Buffer architecture at this [NERSC website](https://sites.google.com/lbl.gov/burstbuffers). I would especially recommend the SC17 tutorial that includes numerous example use cases and tips for tuning I/O performance.

# Performance analysis: parallel vs serial writer routine

I have compared the performance of the parallel and serial routines for writing out Gaussian cube files on the same Cray XC40 machine that I used in my previous post. Because this machine offers Burst Buffer nodes with a total capacity of 36 TB, I have also decided to test whether using the SSDs results in any further performance increase. I will be using two Gaussian cube sizes of 264 × 264 × 264 and 693 × 693 × 693 data points resulting in file sizes of roughly 230 MB and 4.1 GB, respectively. The latter example is slightly exaggerated in size compared to the typical 1-2 GB file sizes that I process in my work to better investigate the effects of using Burst Buffer nodes. The reported timings correspond to the total time needed to write 2 equal sized cube files (containing the numerical values of the electron and spin densities in the tested systems) using the CP2K quantum chemistry code, where the parallel writer routine has been implemented. All MPI I/O settings have been left at their default values. The effect of changing these settings will be explored in the next section. A single Burst Buffer node has been employed in the corresponding tests.

Before proceeding, I would like to note that comparing the I/O performance of the Burst Buffer nodes and the standard parallel file system is difficult due to the following reasons. Firstly, the tested file sizes are very small compared *e.g* to the >100 GB data sets highlighted in the [NERSC tutorials](https://sites.google.com/lbl.gov/burstbuffers). Secondly, the I/O performance is very sensitive to the instantaneous load of the computing system which might vary considerably even on short timescales because the system is in use by other users. Therefore, although all benchmark simulations were executed in consecutive jobs, the timing data should be interpreted with caution.

Let's first take a look at the timing data for the smaller Gaussian cube files. The performance of the serial and parallel routines is compared in Figure 1 as a function of the total number of MPI processes.

![Parallel vs serial write performance for smaller cube file](https://res.cloudinary.com/nholmber/image/upload/v1513770708/mpi_io_write_serialvsparallel_jhqx5m.png)
**Figure 1.** Parallel vs serial write performance for outputting two Gaussian cube files of size 230 MB as a function of the total number of MPI processes.

The benefits of using MPI I/O to output the cube file in parallel are immediately obvious from the above figure. The parallel writer is faster roughly by a factor of 10. Additionally, the time needed by the parallel routine decreases as the number of MPI processes is increased, whereas the opposite behavior is observed for the serial routine. It is not actually the I/O that is getting faster, which is constant at 0.5 seconds, but instead it is the data conversion and other supporting tasks that are accelerated as each processor holds an ever decreasing number of function values. Using Burst Buffer SSD nodes does not improve I/O performance for this particular data set.

To see if there is any advantage to using the Burst Buffer nodes, let's next consider the larger Gaussian cube files. In the following, I shall only use the parallel writer routine because it clearly outperforms the serial version. The timing data with and without Burst Buffer are reported in Figure 2.

![Write performance for larger cube file with and without Burst Buffer SSD nodes](https://res.cloudinary.com/nholmber/image/upload/v1513773328/mpi_io_write_para_c4fj9a.png)
**Figure 2.** Timing data for writing two 4.1 GB Gaussian cube files with and without Burst Buffer (BB) SSD nodes. At left, the total time taken by the writer routine including data conversion, other supporting tasks and I/O. At right, the time spent in the collective MPI write routine *MPI_File_Write_all*.

Focusing first on the total time spent in the routine writing the cube files (Figure 2 at left), it is evident that using the Burst Buffer SSD nodes is beneficial with 192 or 288 MPI processes, but the advantage is lost when the number of MPI processes is further increased to 384. The highest performance improvement, 30 %, is reached with the lowest tested MPI process count. As discussed above in relation to Figure 1, the total time needed to output the files should decrease up to some limit as the number of MPI processes is increased if the I/O performance remains constant. This is unexpectedly not the case when the Burst Buffer nodes are employed.

The cause for this behavior can be understood by separately examining the timings of the collective MPI write calls (*MPI_File_Write_all*), which are reported in Figure 2 at right. This figure reveals that the file write is progressively slower on the Burst Buffer nodes the more MPI processes are in use, whereas the opposite holds for the standard I/O nodes. Overall, the differences on the Burst Buffer nodes are however quite small and it is entirely possible that they are merely the result of fluctuating load on the supercomputer. We can try to improve the I/O performance further by taking a more detailed look at the how the collective I/O operations are implemented, which will be the focus of the next section.


# Fine tuning MPI I/O performance with hints

In collective MPI I/O (routines ending with *_all*), all MPI processes within a communicator group do not necessarily participate in the I/O operations. Instead, the MPI library may heuristically decide to switch on *collective buffering* where special aggregator processes handle all I/O. These aggregators are responsible for distributing/collecting the data to/from the other MPI processes (communication phase). The advantage of collective buffering is that the data gets written and read in larger chunks instead of repeated small requests which hurts performance.

The number of aggregators among other MPI I/O settings can be controlled with environment variables or so-called *hints*. These hints can be set on a file per file basis. It is also possible to get highly detailed timing data for every file accessed with MPI I/O, which is helpful when MPI I/O settings are altered in an attempt to enhance I/O performance. For example, the following environment variables would display all settings related to the MPI and MPI I/O environments as well as switch on MPI I/O performance reports on Cray with MPICH.

{{< codeblock lang="bash" >}}
export MPICH_ENV_DISPLAY=1
export MPICH_MPIIO_HINTS_DISPLAY=1
export MPICH_MPIIO_STATS=1
export MPICH_MPIIO_TIMERS=1
{{< /codeblock >}}

The list of available hints and their default values on Cray with the Lustre parallel file system are the following:

{{< codeblock lang="bash" >}}
PE 0: MPIIO hints for large-cube-SPIN_DENSITY-1_0.cube:
          cb_buffer_size           = 16777216
          romio_cb_read            = automatic
          romio_cb_write           = automatic
          cb_nodes                 = 1
          cb_align                 = 2
          romio_no_indep_rw        = false
          romio_cb_pfr             = disable
          romio_cb_fr_types        = aar
          romio_cb_fr_alignment    = 1
          romio_cb_ds_threshold    = 0
          romio_cb_alltoall        = automatic
          ind_rd_buffer_size       = 4194304
          ind_wr_buffer_size       = 524288
          romio_ds_read            = disable
          romio_ds_write           = disable
          striping_factor          = 1
          striping_unit            = 1048576
          romio_lustre_start_iodevice = 0
          direct_io                = false
          aggregator_placement_stride = -1
          abort_on_rw_error        = disable
          cb_config_list           = *:*
          romio_filesystem_type    = CRAY ADIO:
{{< /codeblock >}}

The hints `romio_cb_*` and `cb_*` define the collective buffering settings. For example, above the hints `romio_cb_read` and `romio_cb_write` are both set to automatic which allows the library to decide whether collective buffering should be used on a file per file basis. The number of aggregators is 1 as defined by the hint `cb_nodes`. The other hints have been explained [here](http://www.idris.fr/media/docs/docu/idris/idris_patc_hints_proj.pdf) or in the MPI manual page available with `man mpi`.

An example of the timing report produced by the environment variable `MPICH_MPIIO_HINTS_DISPLAY=1` is given below. The report corresponds to writing out one of the 4.1 GB Gaussian cube files with 192 MPI processes and no Burst Buffer nodes.

{{< codeblock lang="bash" >}}
+--------------------------------------------------------+
| MPIIO write access patterns for large-cube-SPIN_DENSITY-1_0.cube
|   independent writes      = 106
|   collective writes       = 192
|   independent writers     = 1
|   aggregators             = 1
|   stripe count            = 1
|   stripe size             = 1048576
|   system writes           = 4286
|   aggregators active      = 192,0,0,0 (1, <= 1, > 1, 1)
|   total bytes for writes  = 4382277718 = 4179 MiB = 4 GiB
|   ave system write size   = 1022463
|   read-modify-write count = 0
|   read-modify-write bytes = 0
|   number of write gaps    = 0
|   ave write gap size      = NA
| See "Optimizing MPI I/O on Cray XE Systems" S-0013-20 for explanations.
+--------------------------------------------------------+
+--------------------------------------------------------------------------+
| MPIIO write by phases, all ranks, for large-cube-SPIN_DENSITY-1_0.cube
|   number of ranks writing        =     1
|   number of ranks not writing    =   191
|                                          min         max         ave
|                                    ----------  ----------  ----------
|   open/close/trunc  time         =       0.00        0.00        0.00
|
|   time scale: 1 = 2**4     clock ticks    min         max         ave
|                                    ----------  ----------  ---------- ---
|   total                          =                          760329267
|
|   imbalance                      =       1923        2566        2346  0%
|   open/close/trunc               =     247135      302731      251846  0%
|   local compute                  =      92757      213092       97163  0%
|   wait for coll                  =      14746   752303980   398433146 52%
|   collective                     =      28706       35441       30597  0%
|   exchange/write                 =     373415     2146029      398483  0%
|   data send (*)                  =    7189592   759376475   357649987 47%
|   file write                     =          0   656363834   656363834 86%
|   other                          =       5582       48380       47134  0%
|
|   data send BW (MiB/s)           =                           1899.597
|   raw write BW (MiB/s)           =                           1035.084
|   net write BW (MiB/s)           =                            893.550
|
| (*) send and write overlap when number ranks != number of writers
+--------------------------------------------------------------------------+
{{< /codeblock >}}

The report confirms that indeed only one MPI aggregator was in use and that it achieved a net write bandwidth of 893.550 MiB/s. The report also shows the number of independent (the header lines) and collective (the function value data) writes, the total number of writes and their average size, as well as various other information. The user can try to enhance MPI I/O performance by overriding some of the default settings. MPI I/O hints can be passed to a program through the environment variable `MPICH_MPIIO_HINTS`. For example, the number of MPI aggregators can be increased to 8 for any Gaussian cube file with suffix `.cube` by setting the following hint

{{< codeblock lang="bash" >}}
export MPICH_MPIIO_HINTS="*.cube:cb_nodes=8"
{{< /codeblock >}}

It is a simple matter to systematically test whether changing any MPI I/O setting improves performance. The same simulation just needs to be rerun multiple times with different hints and averaged over multiple simulations with the hints fixed to get more reliable statistics of the write bandwidth.

The number of MPI aggregators is one of the crucial variables to test when using collective I/O operations. Other high priority variables to test have been suggested in this [presentation](http://www.idris.fr/media/docs/docu/idris/idris_patc_hints_proj.pdf). Table 1 shows how the net write bandwidth changes as the number of MPI aggregators is varied between 1 and 192 (implying no collective buffering) when a total of 192 MPI processes are used to write a 4.1 GB Gaussian cube file. The results suggest that better write performance could be achieved by increasing the number of aggregators to 64 from the default value of 1. The improvement is due to better balancing of the time spent communicating and actually writing the data.

**Table 1.** Net write bandwidth as the function of the number of MPI aggregators for writing a 4.1 GB cube file to disk on 192 MPI processes.

| Number of MPI aggregators | Net write bandwidth (MiB/s)  |
|:--------------------------|:----------------------------:|
| 1                         | 893.6                        |
| 2                         | 175.3                        |
| 8                         | 434.2                        |
| 24                        | 601.5                        |
| 48                        | 418.6                        |
| 64                        | 1161.6                       |
| 96                        | 186.4                        |
| 192                       | 436.4                        |


Some additional control settings become available when Burst Buffer SSD nodes are used. The most important setting is the number Burst Buffer nodes which controls how many physical SSDs the output file is striped over. This setting is equivalent to the hint `string_factor` on the Lustre parallel file system. All Burst Buffer settings are controlled through DataWarp. To change the number Burst Buffer nodes, we must first find out the size of each SSD:

{{< codeblock lang="bash" >}}
nholmber@sisu-login2 /work/nholmber/Test/IO >>> scontrol show burst
	Name=cray DefaultPool=wlm_pool Granularity=174416M TotalSpace=36627360M UsedSpace=0
  	Flags=PrivateData
  	StageInTimeout=86400 StageOutTimeout=86400 ValidateTimeout=5 OtherTimeout=300
  	GetSysState=/opt/cray/dw_wlm/default/bin/dw_wlm_cli
{{< /codeblock >}}

The output of the above command shows that each SSD is 174416 MB or roughly 200 GB. The number of allocated Burst Buffer nodes can then be changed by requesting an SSD capacity that is in between adjacent integer multiples of the SSD size. To clarify, the command below, for example, would request 2 Burst Buffer nodes because `3*174416 MB > 450 GB > 2*174416 MB`.

`#DW jobdw type=scratch access_mode=striped capacity=450GB`

For the test system that we have been using in this post, it turns out that changing the number of Burst Buffer nodes does not improve I/O performance when all MPI I/O settings are kept their default values. Increasing the number of MPI aggregators to 64 again yields a slightly better performance. Other settings to test have been comprehensively covered in the [NERSC tutorials](https://sites.google.com/lbl.gov/burstbuffers), and I won't attempt any further optimization in this post.


# Conclusions

In this post, we took a more closer look at collective MPI I/O and how its performance can be tuned via environment variables. We managed to improve I/O performance by increasing the number of MPI aggregators. We also discussed how SSDs are finally becoming integrated in supercomputing systems focusing on Cray's Burst Buffer implementation. A realistic simulation example illustrated that significant time savings can be achieved in I/O intensive workflows by using the SSDs to buffer the data.