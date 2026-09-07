/**
 * Centralized In-Memory API Cache for Lynn C. Jackson Family Archive
 * Prevents redundant multi-megabyte network downloads across tabs, drawers, and modals.
 */

const memoryCache = new Map();

/**
 * Fetches JSON from a URL or returns the in-memory cached promise/data.
 * @param {string} url - API endpoint URL
 * @param {RequestInit} [options] - Optional fetch options
 * @returns {Promise<any>}
 */
export async function fetchCachedJson(url, options = {}) {
  const cacheKey = url;
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  const fetchPromise = (async () => {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status} fetching ${url}`);
      }
      const data = await response.json();
      return data;
    } catch (err) {
      // Clear failed request from cache so subsequent tries can re-attempt
      memoryCache.delete(cacheKey);
      throw err;
    }
  })();

  memoryCache.set(cacheKey, fetchPromise);
  return fetchPromise;
}

/**
 * Clear cached data (useful during development or manual reload)
 */
export function clearApiCache(url) {
  if (url) {
    memoryCache.delete(url);
  } else {
    memoryCache.clear();
  }
}
