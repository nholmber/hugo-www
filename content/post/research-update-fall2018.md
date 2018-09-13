+++
title = "Research Update: September 2018"
categories = ["research"]
archives = ["2018-09"]
date = "2018-09-13"
tag = ["workshop", "research", "CP2K", "computational chemistry", "CDFT"]
keywords = ["workshop", "research", "CP2K", "computational chemistry", "CDFT"]
autoThumbnailImage = "false"
thumbnailImagePosition = "left"
thumbnailImage = "https://res.cloudinary.com/nholmber/image/upload/v1536837895/success-2081167_1280_y0kzjp.jpg"
metaAlignment = "center"
slug = "research-update"

+++

The arrival of a new batch of freshmen is a sure sign of autumn and the start of a new academic semester. I am thrilled to announce that this semester should also be my last one as a Ph.D. candidate because I officially submitted my dissertation for preliminary examination last week. In this post, I will look back on summer 2018 and recap the research projects that I completed during that time.

<!--more-->
{{< image classes="fancybox center clear" src="https://res.cloudinary.com/nholmber/image/upload/v1536837895/success-2081167_1280_y0kzjp.jpg" title="" >}}

Unsurprisingly, I spent a majority of the summer writing my dissertation. This is, however, not a topic I want to discuss in detail today as it deserves its own post later down the line once I'm closer to graduating. I did manage to find the time to work on other research projects in addition to writing. In July, I attended a [computational electrochemistry workshop](https://iwce2018.computational-electrochemistry.org/), where I had the opportunity to present the results from [our latest research paper](https://dx.doi.org/10.1063/1.5038959) that was just published online this week in [The Journal of Chemical Physics](https://aip.scitation.org/journal/jcp). These are two topics that I will be covering in this post.

# New Research Paper: Applications of Constrained DFT to Electrocatalysis Modeling

I must say that I am very satisfied with our latest publication on multiple levels. First of all, this article was the last one that I needed to complete my doctoral degree; in Finland, you generally require 4 peer-reviewed publications before you're allowed to submit an article-based dissertation for preliminary examination and eventually publicly defend it, although the last 1-2 papers don't necessarily have to be accepted for publication by the time of the defense. Second, the project was extremely interesting to work on and allowed me to continue my method development efforts in the [CP2K open-source quantum chemistry software](https://www.cp2k.org). Finally, the paper perfectly wraps up my thesis project as I'll expand upon shortly.

I am pleased to announce that you can access our paper free of charge if you're interested in reading it. The paper was published online in the Journal of Chemical Physics on September 11 and the publisher has made the article open access [on their website](https://dx.doi.org/10.1063/1.5038959) for two weeks starting from the online publication date. After the two week period, feel free to download the accepted manuscript version of the paper which I've included below.

The methods described in the paper have been implemented into [CP2K](https://www.cp2k.org) and are available for immediate use if you want to test them. I've created [a tutorial](https://nholmber.github.io/2017/04/cp2k-build-cray-xc40/) with instructions you can follow to learn how to build the CP2K executable. I plan on extending the [constrained DFT tutorial](https://www.cp2k.org/howto:cdft) that I've written with suitable example simulations for using the newly implemented methodology in the near future. I will also include a brief summary of the relevant theoretical aspects in the tutorial.

I mentioned earlier that the publication is an appropriate conclusion to my Ph.D. thesis project. Concretely, I began this project by developing models for carbon nanotube-catalyzed hydrogen evolution (papers [1](https://dx.doi.org/10.1021/acs.jpcc.5b04739)-[2](https://dx.doi.org/10.1021/acs.jpclett.5b01846)), and then took a brief detour to implement methods for modeling charge transfer phenomena by coding a constrained DFT framework in CP2K (paper [3](https://dx.doi.org/10.1021/acs.jctc.6b01085)). In my final paper, I combined ideas and methods from paper 3 and applied them to the types of systems that I previously looked at in publications 1-2. I find it highly satisfactory that my Ph.D. research came full circle in my last paper.

> **Copyright notice.** This article may be downloaded for personal use only. Any other use requires prior permission of the author and AIP Publishing. The following article appeared in The Journal of Chemical Physics, 149, 104702 (2018), and may be found online at https://doi.org/10.1063/1.5038959. The following document is the accepted manuscript version of the article.

<iframe src="https://drive.google.com/file/d/1bvWK6cmr7ss_Wdf_jSTvfOEIlZIpa_DB/preview" width="640" height="480"></iframe>

# Presentation at the International Workshop on Computational Electrochemistry

I really wish [this workshop](https://iwce2018.computational-electrochemistry.org/) would have been arranged earlier into my doctoral studies. The speakers at the workshop were true experts in computational electrochemistry, and their presentations managed to cover all of the challenging aspects that researchers face in this field of theoretical modeling. The excellent workshop was completed by high-quality poster presentations. I must say that I learned a lot at the workshop and got many new ideas on how one could potentially continue the research that I started during my Ph.D.

I wish to thank the workshop organizers for giving me the privilege to present at the workshop. The feedback that I received from the expert audience truly helped me in refining my thoughts for the dissertation writing process. You can find the slides I used in my presentation below if you're interested.

**By the way**, I figured out how to easily embed fonts in a PowerPoint presentation with proprietary fonts so that the PDF is properly rendered on SlideShare. You simply need to first convert the PDF to a PostScript file with `pdftops`, and then convert the resulting file back to PDF format with `pdf2ps`. This way any unembedded proprietary fonts get substituted with free alternatives that more or less match the originals.

<iframe src="//www.slideshare.net/slideshow/embed_code/key/EzefVMzV58nkQV" width="595" height="485" frameborder="0" marginwidth="0" marginheight="0" scrolling="no" style="border:1px solid #CCC; border-width:1px; margin-bottom:5px; max-width: 100%;" allowfullscreen> </iframe> <div style="margin-bottom:5px"> <strong> <a href="//www.slideshare.net/NicoHolmberg/using-constrained-dft-for-simulating-the-hydrogen-evolution-reaction" title="Using constrained DFT for simulating the hydrogen evolution reaction " target="_blank">Using constrained DFT for simulating the hydrogen evolution reaction </a> </strong> from <strong><a href="https://www.slideshare.net/NicoHolmberg" target="_blank">Nico Holmberg</a></strong> </div>
