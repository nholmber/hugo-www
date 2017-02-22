+++
tags = ["hugo","github"]
categories = ["web"]
archives = ["2017-02"]
date = "2017-02-22"
title = "Welcome to my website!"
keywords = [""]
autoThumbnailImage = "false"
thumbnailImagePosition = "top"
thumbnailImage =  "https://res.cloudinary.com/nholmber/image/upload/v1487771617/welcome-700x185_juytkh.jpg"
coverImage = "https://res.cloudinary.com/nholmber/image/upload/v1487770746/welcome-1000x667_pxorv7.jpg"
metaAlignment = "center"
slug = "welcome"

+++

Greetings and welcome! You have stumbled upon the personal website and blog of Nico Holmberg, a 26 year old Finn pursuing a doctoral degree in Computational Quantum Chemistry. Feel free to check out my [profile](../../../profile) for more information about me, my professional projects and other interests! 
<!--more-->

I intend to keep this blog mostly professional by writing about topics related to my ongoing projects. Currently, I am mainly focusing on the development of new tools to model charge transfer related phenomena, which I have implemented in the versatile open-source software package called [**CP2K**](https://www.cp2k.org/) ([<i class="fa fa-lg fa-github" style="color:#08b470ff"></i>](https://github.com/nholmber "GitHub Profile")). All of my research projects are intimately linked with [high-performance computing](https://en.wikipedia.org/wiki/High-performance_computing), and I plan on covering this subject in future posts from the perspective of a chemist with no formal background in computer science but with an avid desire to learn. In my first post, however, I will be discussing something entirely unrelated by briefly describing how I created the website that you are currently browsing.

I have virtually no experience in `HTML`, `JavaScript`, or web development in general. Among my other duties as a doctoral student, I am nevertheless responsible for maintaining our [research group's website](https://chemistry.aalto.fi/en/research/computational_chemistry/information/). This website, along with the rest of our [university's](https://www.aalto.fi/en/ "Aalto University") website, is built on [Midgard CMS](https://en.wikipedia.org/wiki/Midgard_(software)), a framework where editing and posting content is simple through a <acronym title="What You See Is What You Get">WYSIWYG</acronym> interface, saving me valuable time towards other tasks. While I appreciate the ease of use provided by feature-rich CMS services such as the ever popular [WordPress](https://wordpress.org/), I wanted to go in a different direction with my personal website. At the time of writing this post, my expectations for this website are that it will contain a modest amount of content and that most elements will be *static* in nature. Primarily for these reasons, I have opted to create a static website rather than a dynamical one. Take a look at this good introductory [article](http://noahveltman.com/static-dynamic/) comparing static and dynamic websites if your unfamiliar with the concepts. 

In the diverse field of static website generators and hosting solutions, I settled on a combination of [Hugo](https://gohugo.io/) and [GitHub Pages](https://pages.github.com/), a choice that was greatly influenced by the current popularity of the combination. The advantages of GitHub are obvious. Besides being free, the website is hosted as a standard GitHub repository like any other programming project, which facilitates easy version controlling, collaborative development via pull requests, and command line deployment of new content. Hugo, on the other hand, is a fast, general-purpose website creation tool written in [Go](https://golang.org/) which comes bundled with many nifty features, such as a built-in HTTP server for previewing your website, support for various types of content, and custom themes. For users looking to quickly create a website, setting up a minimal Hugo installation is very simple. Just download a Hugo binary suitable for you OS, browse for a theme of your liking, and that's it --- no dependencies needed! The binary renders all of your content into organized `HTML` files that form the actual website. Creating new content is also straightforward because every entry is a [`Markdown`](https://en.wikipedia.org/wiki/Markdown) document, possibly incorporating Hugo [shortcodes](https://gohugo.io/extras/shortcodes/) or snippets of custom `HTML` code to enable richer content, which can be edited in any text editor. Hosting your Hugo-powered website on GitHub is no hassle either thanks to the availability of a clear [step-by-step tutorial](https://gohugo.io/tutorials/github-pages-blog/).
