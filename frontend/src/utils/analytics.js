/**
 * Google Analytics 4 (GA4) Integration Utility
 * Written In The Genome — Genetic Archive
 */

export const GA_MEASUREMENT_ID = window.VITE_GA_MEASUREMENT_ID || 'G-MEASUREMENT_ID';

export const initGA = (measurementId = GA_MEASUREMENT_ID) => {
  if (typeof window === 'undefined') return;

  // Don't re-initialize if script already loaded
  if (document.getElementById('ga-gtag')) return;

  const script = document.createElement('script');
  script.id = 'ga-gtag';
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  window.gtag = gtag;

  gtag('js', new Date());
  gtag('config', measurementId, {
    page_location: window.location.href,
    page_title: document.title,
  });
};

export const trackPageView = (path, title) => {
  if (typeof window !== 'undefined') {
    // 1. Google Analytics 4 Page View
    if (window.gtag) {
      window.gtag('event', 'page_view', {
        page_path: path,
        page_title: title || document.title,
      });
    }

    // 2. Jetpack Stats Event Queue Push
    if (window._stq) {
      window._stq.push(['view', {
        v: 'ext',
        blog: 'writteninthegenome.blog',
        srv: 'familyarchive.writteninthegenome.blog',
        subpath: path
      }]);
    }
  }
};

export const trackEvent = (action, category, label, value) => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', action, {
      event_category: category,
      event_label: label,
      value: value,
    });
  }
};
