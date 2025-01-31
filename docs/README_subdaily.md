### subdaily<a name="module6"></a>

This module is meant for RH measurements that have a subdaily component. It is not strictly 
for water levels, but that is generally where it should be used. There are 
two main goals for this code:

- consolidate daily result files and find/remove outliers
- apply the [RHdot correction](https://www.kristinelarson.net/wp-content/uploads/2015/10/LarsonIEEE_2013.pdf)

If you want to do your own QC, you can simply cat the files in your results area. As an example, after you have 
run <code>gnssir</code> for a station called sc02 in the year 2021:

<code>cat $REFL_CODE/2021/sc02/*.txt >sc02.txt</code>

If you would prefer to use our code, it is pretty straightforward. It has two sections.  The first 
minimally requires the station name and year:

<code>subdaily sc02 2021 </code>

It picks up all result files from 2021, sorts and concatenates them. If you only want to 
look at a subset of days, you can set -doy1 and/or -doy2. The output file location
is sent to the screen. <code>subdaily</code> then tries to remove large outliers 
by using a standard deviation test. This can be controlled at the command line. Example figures:

Results are presented with azimuth and amplitude colors to help you modify QC choices or azimuth mask:

<img src="https://github.com/kristinemlarson/gnssrefl/blob/master/docs/sc02-1.png" width="600"/>

<img src="https://github.com/kristinemlarson/gnssrefl/blob/master/docs/sc02-2.png" width="600"/>

Whle this code is meant to be used AFTER you have chosen an analysis strategy, you can 
apply new azimuth and amplitude constraints on the commandline, <code>-azim1, azim2, ampl</code>.

The second section of <code>subdaily</code> is related to the RHdot correction. You must explicitly ask for it. 
There are lots of ways to apply the RHdot correction - I am only providing a simple one at this point.  
The RHdot correction requires you know 
- the average of the tangent of the elevation angle during an arc, 
- edot, elevation angle rate of change with respect to time) 
- RHdot (RH rate of change with respect to time)  

The first two are trivial to compute and are included in the results file in column 13 as the edotF. 
This edot factor has units of rad/(rad/hour), or hours. So if you know RHdot in units of meters/hour, 
you can get the correction by simple multiplication. 

Computing RHdot is the trickiest part of calculating the RHdot correction.
And multiple papers have been written about it. If you have a 
well-observed site (lots of arcs and minimal gaps), you can use the RH 
data themselves to estimate a smooth model for RH (via cubic splines) and 
then just back out RHdot. This is what is done in <code>subdaily</code> (if and only if you invoke -rhdot True). 
It will also make a second effort to remove outliers.  
Note: if you have a site with a large RHdot correction, you should be cautious of removing too many
outliers in the first section of this code as this is really signal, not noise. You can set the outlier criterion 
with <code>-spline_outlier N</code>, where N is in meters. It also makes an attempt to remove frequency biases. 

There are other ways to compute the RHdot correction:

- computing tidal coefficients, and then iterating using the forward predictions of the tidal fit(Larson et al. 2013b)
- estimating RHdot effect simultaneously with tidal coefficient (Larson et al. 2017). 
- low-order tidal fit (Lofgren et al 2014)
- direct inversion of the SNR data (Strandberg et al 2016 , Purnell et al. 2021)
- estimate a rate and an acceleration term (Tabibi et al 2020)

I am working to make some of these other methods available in this package.

Here are some results from the SC02 site again - but now from the second section of the code. 
In the bottom panel you can see that applying the RHdot correction at this site improves the 
RMS fit from 0.15 to 0.11 meters.

<img src="https://github.com/kristinemlarson/gnssrefl/blob/master/docs/sc02-3.png" width="600"/>

After the RHdot correction has been applied, the code then estimates a new spline fit and 
removes frequency-specific biases. Stats for this fit with respect to the spline fit 
are printed to the screen. Three-sigma outliers with respect to the new fit are removed.
In this example the RMS improves from 0.11 to 0.09 m. 

<img src="https://github.com/kristinemlarson/gnssrefl/blob/master/docs/sc02-5.png" width="600"/>

Here is an example of a site (TNPP) where the RHdot correction is 
even more important (I apologize for color choice here. The 
current code uses more color-blindness-friendly colors):

<img src="https://github.com/kristinemlarson/gnssrefl/blob/master/docs/tnpp_rhdot2.png" width="600"/>

After removing the RHdot effect and frequency biases, the RMS improves from 0.244 to 0.1 meters.

<img src="https://github.com/kristinemlarson/gnssrefl/blob/master/docs/tnpp_final.png" width="600"/>

Comment: if you have an existing file with results, you can just run the second part of the code. 
If the input file is called test.txt, you would call it as:

<code>subdaily sc02 2021 -splinefile test.txt -rhdot True</code>

<hr>

