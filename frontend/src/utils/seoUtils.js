/**
 * SEO & JSON-LD Structured Data Utilities for Delmarva Genealogy Archive
 * Generates Schema.org Person, GenealogicalRecord, and BreadcrumbList markup.
 */

export function generatePersonJsonLd(person) {
  if (!person) return null;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Person',
    '@id': `https://genealogy.writteninthegenome.blog/person/${person.id}`,
    'name': person.name,
    'alternateName': person.aliases || [],
    'gender': person.gender === 'M' ? 'Male' : person.gender === 'F' ? 'Female' : undefined,
    'birthDate': person.birth_date || undefined,
    'birthPlace': person.birth_place ? { '@type': 'Place', 'name': person.birth_place } : undefined,
    'deathDate': person.death_date || undefined,
    'deathPlace': person.death_place ? { '@type': 'Place', 'name': person.death_place } : undefined,
    'description': person.bio || `Genealogical record for ${person.name} in the Delmarva & Nanticoke Archive.`,
    'url': window.location.href,
  };

  if (person.parents && person.parents.length > 0) {
    jsonLd.parent = person.parents.map(p => ({
      '@type': 'Person',
      'name': p.name,
      '@id': `https://genealogy.writteninthegenome.blog/person/${p.id}`
    }));
  }

  if (person.spouses && person.spouses.length > 0) {
    jsonLd.spouse = person.spouses.map(s => ({
      '@type': 'Person',
      'name': s.name,
      '@id': `https://genealogy.writteninthegenome.blog/person/${s.id}`
    }));
  }

  return jsonLd;
}

export function generateBreadcrumbJsonLd(items) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    'itemListElement': items.map((item, idx) => ({
      '@type': 'ListItem',
      'position': idx + 1,
      'name': item.name,
      'item': item.url ? `https://genealogy.writteninthegenome.blog${item.url}` : undefined
    }))
  };
}

export function injectJsonLdScript(id, data) {
  let existingScript = document.getElementById(id);
  if (!existingScript) {
    existingScript = document.createElement('script');
    existingScript.id = id;
    existingScript.type = 'application/ld+json';
    document.head.appendChild(existingScript);
  }
  existingScript.textContent = JSON.stringify(data, null, 2);
}
