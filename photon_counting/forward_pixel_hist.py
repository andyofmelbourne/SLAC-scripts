"""
Forward simulate a pixel histogram

with the following paramters:
    adus       
    dark_peak  
    sigma_to_pix 
    photon_sig   
    photons     
    ns         
    photon_adu
    pix_per_pix 
    pix_pad    
    model     

see hist_model for details.
"""

import numpy as np
import scipy.ndimage.filters
import functools
import scipy.optimize
import scipy.special

def single_photon_model(adus, sigma_to_pix, photon_adu, pix_per_pix, pix_pad, model):
    if model=='gaus':
        return single_photon_model_gaus(adus, sigma_to_pix, photon_adu, pix_per_pix, pix_pad, model)
    
    N = pix_per_pix * pix_pad
    
    i, j   = np.mgrid[0: N: 1, 0: N: 1]
    if model=='gaus':
        photon_cloud = np.exp( - ((i - N/2).astype(np.float64)**2 + (j - N/2).astype(np.float64)**2) \
                              / (2. * float(sigma_to_pix*pix_per_pix)**2 ))
    if model=='circle':
        r = np.sqrt( (i-N/2).astype(np.float64)**2 + (j-N/2).astype(np.float64)**2)
        photon_cloud = (r < float(sigma_to_pix*pix_per_pix)).astype(np.float64)
    
    photon_cloud = photon_cloud / np.sum(photon_cloud)
    
    # make the pixel
    i, j             = np.mgrid[0: pix_per_pix : 1, 0 : pix_per_pix : 1]
    pixels           = (i, j)
    pixel            = np.zeros_like(photon_cloud)
    pixel[pixels]    = photon_adu
    
    # convolve
    Pixel        = np.fft.fft2(pixel)
    Photon_cloud = np.fft.fft2(photon_cloud)
    conv         = np.abs(np.fft.ifft2( Pixel * np.conj(Photon_cloud) ))
    
    hist, bins = np.histogram(np.abs(conv).ravel(), bins = np.arange(adus + 1))
    
    s01    = hist.astype(np.float64)
    s01[0] = 0
    s01    = s01 / np.sum(s01)
    return s01


def single_photon_model_gaus(adus, sigma_to_pix, photon_adu, pix_per_pix, pix_pad, model):
    i     = np.arange(int(pix_per_pix/2), int(pix_pad*pix_per_pix/2.), 1.)
    
    sig = sigma_to_pix * pix_per_pix
    y   = 0.5 * (scipy.special.erfc((i-pix_per_pix) / (np.sqrt(2.) * sig)) - scipy.special.erfc(i / (np.sqrt(2.) * sig)))
    
    yx, yy = np.meshgrid(y, y, indexing='ij', copy=False)
    y_xy = yx * yy * photon_adu
    
    hist, bins = np.histogram(y_xy.ravel(), bins=np.arange(adus + 1)) 
    
    s01    = hist.astype(np.float64)
    s01[0] = 0
    s01    = s01 / np.sum(s01)
    return s01


def hist_model(s0, sigma_to_pix = 0.1, photon_sig = 1.5, photon_adu = 30, \
               pix_per_pix = 256, pix_pad = 3, model = 'gaus', photons = 3, \
               ns = 0.2, poisson = True, full_output=False):
    """
    Forward simulate a pixel histogram
    
    Parameters
    ----------
    s0 : numpy.ndarray, (N,)
        The (normalised) histogram of the zero order (dark) values on the pixel. Where:
        
        N : is the number of adu values of the pixel

    sigma_to_pix : float 
        The ratio of the sigma width of the photon cloud to the pixel width.
        
    photon_sig : float 
        The sigma width (in adus) of the gaussian to blur the histogram with.

    photons : float 
        The number of photons to include in the forward model i.e. single photon events or 
        double photon events e.t.c.

    ns : numpy.ndarray, (photons,) 
        The expectation value of the number of events per shot for each of the 
        single, double ... number of photons.

    photon_adu : float
        The adu value of the peak of the single photon distribution.
        
    pix_per_pix : int
        The number of array pixels per physical pixel in the simulation along each dimension.

    pix_pad : int
        The number of pixels around the central pixel in the simulation along each dimension. 
        You should probably stick to 3 unless the photon cloud is huge (large sigma_to_pix).

    model : 'gaus' or 'circle'
        The shape of the photon cloud on the detector.

    poisson : True or False, optional, default (True)
        If True then poisson counting statistics is used to estimate the expectation value
        of the double, triple e.t.c events based on the scalar value of ns.

    full_output : True or False, optional, default (True)
        If True then return a python dictionary with extra diagnostics.

    Returns
    -------

    hist : numpy.ndarray, float64, (N,)
        The forward model of the pixel histogram.

    info : dictionary (only returned if full_output is True)
        info = {
                's01': s01,       The single photon adu distribution 
                                  before convolution with a gaussian 
                                  (sigma = photon_sig)
                's1' : s1,        As above but after the convolution
                'ss' : ss,        The dark, single photon, 
                                  double photon ... adu distibutions
                                  (all normalised)
                'fits' : fits,    As above but weighted by the 
                                  expectation values (ns)
                }
            
    """
    import math
    if poisson :
        lamb = ns
        ns = np.zeros((photons+1,), dtype=np.float64)
        for k in np.arange(photons+1):
            ns[k] = lamb**k * np.exp(-lamb) / float(math.factorial(k))
    
        ns = ns / np.sum(ns)
    
    s01 = single_photon_model(s0.shape[0], sigma_to_pix, photon_adu, pix_per_pix, pix_pad, model)
    
    s1  = scipy.ndimage.filters.gaussian_filter(s01, photon_sig)
    
    ss    = np.zeros((photons + 1, s1.shape[0]), dtype=s1.dtype)
    ss[0] = s0
    ss[1] = s1
    
    for i in range(2, ss.shape[0], 1):
        ss[i] = np.convolve(ss[i-1], s1, mode='full')[:s0.shape[0]]

    for i in range(1, ss.shape[0], 1):
        ss[i] = np.convolve(ss[i], s0, mode='full')[:s0.shape[0]]
        ss[i] = ss[i] / np.sum(ss[i])

    fits = ss * ns[:, np.newaxis]
    fit  = np.sum(fits, axis=0)
    if full_output :
        info = {
                's01': s01, 
                's1' : s1,
                'ss' : ss,
                'fits' : fits,
                }
        return fit, info
    else :
        return fit

from pylab import *
def figures(sigma_to_pix, pix_per_pix, photon_adu, photon_sig, ss, adus):
    def gaus(sig, N=900):
        i, j   = np.mgrid[0: N: 1, 0: N: 1]
        photon_cloud = np.exp( - ((i - N/2).astype(np.float64)**2 + (j - N/2).astype(np.float64)**2) \
                           / (2. * float(sig*N/3.)**2 ))
        return photon_cloud

    def gaus_pix(sigma, N=900, photon_adu=30.):
        sig = sigma * N / 3.
        i   = np.arange(-N/3, 2*N/3, 1.)
        y   = 0.5 * (scipy.special.erfc((i-N/3) / (np.sqrt(2.) * sig)) - scipy.special.erfc(i / (np.sqrt(2.) * sig)))
        
        yx, yy = np.meshgrid(y, y, indexing='ij', copy=False)
        y_xy = yx * yy
        return y_xy

    def get_p1(pix_h, photon_adu = 30, adus=30):
        hist, bins = np.histogram(photon_adu * pix_h.ravel(), bins=np.arange(adus + 1)) 
        
        s01    = hist.astype(np.float64)
        s01[0] = 0
        s01    = s01 / np.sum(s01)
        return s01

    def get_direct_neighbour_diag(pix_h, photon_adu = 30, adus = 30):
        N = pix_h.shape[0]
        direct    = pix_h[N/3 : 2*N/3, N/3 : 2*N/3]
        neighbour = pix_h[0 : N/3, N/3 : 2*N/3]
        diag      = pix_h[0 : N/3, 0 : N/3]
        
        hist_dir, bins = np.histogram(photon_adu * direct.ravel(), bins=np.arange(adus + 1)) 
        hist_nei, bins = np.histogram(photon_adu * neighbour.ravel(), bins=np.arange(adus + 1)) 
        hist_dia, bins = np.histogram(photon_adu * diag.ravel(), bins=np.arange(adus + 1)) 
        
        hist_nei *= 4
        hist_dia *= 4
        
        ss    = []
        for h in [hist_dir, hist_nei, hist_dia]:
            ss.append(h.astype(np.float64))
            ss[-1][0] = 0
        ss = np.array(ss)
        ss = ss / np.sum(ss)
        return ss
    
    N = 3 * pix_per_pix
    sig = sigma_to_pix

    gauss = gaus(sig, N )
    pix_h = gaus_pix(sig, N, photon_adu)
    s01s  = get_p1(pix_h, photon_adu, photon_adu)

    gs = GridSpec(1+2,4)

    i = 0
    ax = subplot(gs[i, 0])
    ax.imshow(gauss, 'Greys')
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    alpha = 0.7
    color = 'k'
    ax.axhline(y=pix_per_pix, color=color, alpha=alpha)
    ax.axhline(y=2*pix_per_pix, color=color, alpha=alpha)
    ax.axvline(x=pix_per_pix, color=color, alpha=alpha)
    ax.axvline(x=2*pix_per_pix, color=color, alpha=alpha)
        
    ax = subplot(gs[i, 1])
    ax.imshow(pix_h, 'Greys')
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    alpha = 0.7
    color = 'k'
    ax.axhline(y=pix_per_pix, color=color, alpha=alpha)
    ax.axhline(y=2*pix_per_pix, color=color, alpha=alpha)
    ax.axvline(x=pix_per_pix, color=color, alpha=alpha)
    ax.axvline(x=2*pix_per_pix, color=color, alpha=alpha)
        
    ax = subplot(gs[i, 2:4])
    ax.bar(np.arange(len(s01s)), s01s, width=1.0, alpha=0.6, color='r', label=r'$\sigma_p$ = ' + str(sig))
    ax.yaxis.tick_right()
    ax.set_xlim([0, photon_adu+1])
    #ax.set_ylim([0, 0.3])
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('right')
    ax.legend(loc='upper right')
    ax.set_xlabel('adu')
    ax.set_ylabel('probability')
    ax.yaxis.set_label_position("right")
    ax.legend(loc='upper left')

    #fig = gcf()
    #fig.set_size_inches(5.5,4.5/3.)
    
    #fig.savefig('s01.png', dpi=300, bbox_inches='tight')

    N = pix_h.shape[0]
    direct    = pix_h[N/3 : 2*N/3, N/3 :2*N/3]
    neighbour = pix_h[0 : N/3, N/3 : 2*N/3]
    diag      = pix_h[0 : N/3, 0:N/3]

    ss01 = get_direct_neighbour_diag(pix_h, photon_adu, adus = photon_adu)
    s0   = ss[0] 
    ss1  = []
    for s in ss01 :
        ss1.append(np.zeros_like(ss[0]))
        ss1[-1][:len(s)] = s
        ss1[-1] = scipy.ndimage.filters.gaussian_filter(ss1[-1], photon_sig)
        ss1[-1] = np.convolve(ss1[-1], s0, mode='full')[:s0.shape[0]]
    ss1 = np.array(ss1)
    ss1 = ss1 / np.sum(ss1)

    #gs = GridSpec(2,1)

    ax = subplot(gs[1, :])
    for i, si in enumerate(ss) :
        ax.plot(adus, si, linewidth=3, alpha = 0.6, label = str(i)+' photon')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.set_xlim([-20, 70])
    ax.legend(fontsize=10)
    ax.set_ylabel('probability')

    ylim = ax.get_ylim()

    ax = subplot(gs[2, :])
    ax.plot(adus, np.sum(ss1, axis=0), 'g', linewidth=3, alpha = 0.6, label = '1 photon')
    ax.plot(adus, ss1[0], 'b', label = 'direct hit')
    ax.plot(adus, ss1[1], 'r', label = 'neighbour hit')
    ax.plot(adus, ss1[2], 'm', label = 'diagonal hit')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.set_xlim([-20, 60])
    ax.legend(fontsize=10)
    ax.set_xlabel('adu')
    ax.set_ylabel('probability')

    fig = gcf()
    fig.set_size_inches(5.5,1.5*4.5)
    fig.savefig('zero_single_double.png', dpi=300, bbox_inches='tight')


if __name__ == '__main__':
    # Define the pixel parameters
    adus = np.arange(-100, 401, 1).astype(np.float64)
    dark_sigma = 5. 
    dark_peak  = np.exp( -adus**2 / (2. * dark_sigma**2)) dark_peak  = dark_peak / np.sum(dark_peak)

    sigma_to_pix = 0.1
    photon_sig   = 1.5
    photons      = 3
    ns           = np.array([0.5, 0.2, 0.1, 0.1])
    photon_adu   = 30
    pix_per_pix  = 300
    pix_pad      = 3
    model        = 'gaus'
    
    hist, info = hist_model(dark_peak, sigma_to_pix, photon_sig, photons, ns, photon_adu, pix_per_pix, pix_pad, model, True)

    figures(sigma_to_pix, pix_per_pix, photon_adu, photon_sig, info['ss'], adus)
    
