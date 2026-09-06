/**
 * citationGenerator.js
 * ====================
 * Formats scholarly academic citations and genealogical proof references
 * adhering to Chicago Manual of Style (17th ed.) and Elizabeth Shown Mills'
 * "Evidence Explained: Citing History Sources from Artifacts to Cyberspace".
 * Also generates standard GEDCOM 5.5.1 individual lineage excerpts.
 */

const REPOSITORY_NAME = "Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Archive";
const REPOSITORY_URL = typeof window !== 'undefined' ? window.location.origin : "https://lynncjackson-genealogy.vercel.app";

function formatDate(date) {
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function generateEvidenceExplainedCitation(item, type = 'person') {
  const accessDate = formatDate(new Date());
  const year = new Date().getFullYear();

  if (type === 'person') {
    const person = item.person || item;
    const pid = person.person_id;
    const name = person.name || `${person.first_name || ''} ${person.married_last_name || person.maiden_name || ''}`.trim();
    const sourcePage = person.source_page || "Archival Survey Collection";
    const vitals = [];
    if (person.birth_info && person.birth_info !== 'unknown') vitals.push(`b. ${person.birth_info}`);
    if (person.death_info && person.death_info !== 'unknown') vitals.push(`d. ${person.death_info}`);
    const vitalStr = vitals.length > 0 ? ` (${vitals.join(', ')})` : '';

    return {
      referenceNote: `${REPOSITORY_NAME}, digital evidence database and genealogical proof repository (${REPOSITORY_URL} : accessed ${accessDate}), individual profile and evidence model for ${name}${vitalStr}, ID #${pid}; original records preserved from "${sourcePage}".`,
      subsequentNote: `Jackson and Mitsawokett Family Archive, individual profile for ${name} (ID #${pid}).`,
      sourceListEntry: `Jackson, Lynn C., and Mitsawokett Preservation Project. Delmarva Afro-Indigenous Remnant Community Preservation Database. Online repository, proof arguments, and photographic survey. ${REPOSITORY_URL} : ${year}.`
    };
  }

  if (type === 'obituary') {
    const decName = item.deceased_name || "Historical Obituary";
    const dDate = item.death_date ? `, died ${item.death_date}` : '';
    const cem = item.cemetery_location ? `, burial in ${item.cemetery_location}` : '';
    return {
      referenceNote: `"${decName} Obituary"${dDate}${cem}, preserved in ${REPOSITORY_NAME}, Obituary Vault (${REPOSITORY_URL} : accessed ${accessDate}).`,
      subsequentNote: `Jackson and Mitsawokett Archive, obituary for ${decName}.`,
      sourceListEntry: `Jackson, Lynn C., and Mitsawokett Preservation Project. Obituary and Memorial Vault. ${REPOSITORY_URL} : ${year}.`
    };
  }

  if (type === 'document') {
    const title = item.title || item.normalized_filename || item.filename || "Historical Document";
    return {
      referenceNote: `"${title}", historical primary record, preserved in ${REPOSITORY_NAME} (${REPOSITORY_URL} : accessed ${accessDate}).`,
      subsequentNote: `Jackson and Mitsawokett Archive, record "${title}".`,
      sourceListEntry: `Jackson, Lynn C., and Mitsawokett Preservation Project. Delmarva Primary Record Transcriptions and Deeds. ${REPOSITORY_URL} : ${year}.`
    };
  }

  return { referenceNote: `${REPOSITORY_NAME}, accessed ${accessDate}.`, subsequentNote: "", sourceListEntry: "" };
}

export function generateChicagoCitation(item, type = 'person') {
  const accessDate = formatDate(new Date());

  if (type === 'person') {
    const person = item.person || item;
    const pid = person.person_id;
    const name = person.name || "Individual";
    const url = `${REPOSITORY_URL}/#person-${pid}`;

    return {
      footnote: `${REPOSITORY_NAME}, s.v. "${name}," Individual Record #${pid}, accessed ${accessDate}, ${url}.`,
      bibliography: `${REPOSITORY_NAME}. "${name}" (ID #${pid}). Delmarva Afro-Indigenous Preservation Repository. Accessed ${accessDate}. ${url}.`
    };
  }

  if (type === 'obituary') {
    const name = item.deceased_name || "Obituary";
    return {
      footnote: `"${name}," obituary, ${REPOSITORY_NAME}, accessed ${accessDate}, ${REPOSITORY_URL}.`,
      bibliography: `${REPOSITORY_NAME}. "${name}." Obituary Vault. Accessed ${accessDate}. ${REPOSITORY_URL}.`
    };
  }

  if (type === 'document') {
    const title = item.title || item.normalized_filename || "Document";
    return {
      footnote: `"${title}," ${REPOSITORY_NAME}, accessed ${accessDate}, ${REPOSITORY_URL}.`,
      bibliography: `${REPOSITORY_NAME}. "${title}." Primary Document Catalog. Accessed ${accessDate}. ${REPOSITORY_URL}.`
    };
  }

  return { footnote: "", bibliography: "" };
}

export function generateBibTeX(item, type = 'person') {
  const year = new Date().getFullYear();
  const id = (item.person?.person_id || item.person_id || item.id || 'record').toString();
  const name = item.person?.name || item.name || item.deceased_name || item.title || 'Record';

  return `@misc{delmarva_${id},
  author = {{Lynn C. Jackson and Mitsawokett Preservation Project}},
  title = {${name} - Delmarva Afro-Indigenous Community Archive},
  year = {${year}},
  url = {${REPOSITORY_URL}},
  note = {Accessed: ${formatDate(new Date())}}
}`;
}

export function generateGedcomExcerpt(profile) {
  const person = profile.person || profile;
  const facts = profile.facts || [];
  const rels = profile.relationships || [];

  const pid = person.person_id || 1;
  const firstName = person.first_name || person.name?.split(' ')[0] || '';
  const lastName = person.married_last_name || person.maiden_name || person.name?.split(' ').slice(1).join(' ') || '';

  let lines = [
    '0 HEAD',
    '1 SOUR LYNNCJACKSON_ARCHIVE',
    '2 VERS 2.0',
    '2 NAME Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Archive',
    '1 GEDC',
    '2 VERS 5.5.1',
    '2 FORM LINEAGE-LINKED',
    '1 CHAR UTF-8',
    `0 @I${pid}@ INDI`,
    `1 NAME ${firstName} /${lastName}/`,
    `2 GIVN ${firstName}`,
    `2 SURN ${lastName}`
  ];

  if (person.maiden_name) {
    lines.push(`1 _MARNM ${person.married_last_name || ''}`);
    lines.push(`1 _MDN ${person.maiden_name}`);
  }

  // Birth
  const birthFact = facts.find(f => f.fact_type?.toLowerCase() === 'birth');
  if (birthFact || (person.birth_info && person.birth_info !== 'unknown')) {
    lines.push('1 BIRT');
    const bDate = birthFact?.date_string || person.birth_info;
    if (bDate && bDate !== 'unknown') lines.push(`2 DATE ${bDate}`);
    if (birthFact?.place_string) lines.push(`2 PLAC ${birthFact.place_string}`);
  }

  // Death
  const deathFact = facts.find(f => f.fact_type?.toLowerCase() === 'death');
  if (deathFact || (person.death_info && person.death_info !== 'unknown')) {
    lines.push('1 DEAT');
    const dDate = deathFact?.date_string || person.death_info;
    if (dDate && dDate !== 'unknown') lines.push(`2 DATE ${dDate}`);
    if (deathFact?.place_string) lines.push(`2 PLAC ${deathFact.place_string}`);
  }

  // Notes & Evidence
  if (person.notes) {
    lines.push(`1 NOTE ${person.notes}`);
  }
  lines.push(`1 SOUR @S_ARCHIVE@`);
  lines.push(`2 PAGE Individual ID #${pid}`);

  // Relationships
  rels.forEach((r, idx) => {
    if (r.relationship_type === 'child_of' || r.relationship_type === 'parent') {
      lines.push(`1 NOTE Kinship: ${r.relationship_type} with ${r.rel_name} (ID #${r.rel_id})`);
    } else if (r.relationship_type === 'spouse' || r.relationship_type === 'married') {
      lines.push(`1 FAMS @F${idx + 1}@`);
    }
  });

  // Source Record
  lines.push('0 @S_ARCHIVE@ SOUR');
  lines.push(`1 TITL ${REPOSITORY_NAME}`);
  lines.push(`1 AUTH Lynn C. Jackson & Mitsawokett Preservation Project`);
  lines.push(`1 REPO @REPO1@`);
  lines.push(`0 @REPO1@ REPO`);
  lines.push(`1 NAME ${REPOSITORY_NAME}`);
  lines.push(`1 ADDR ${REPOSITORY_URL}`);
  lines.push('0 TRLR');

  return lines.join('\n');
}

export function downloadGedcomFile(profile) {
  const person = profile.person || profile;
  const gedContent = generateGedcomExcerpt(profile);
  const cleanName = (person.name || `person_${person.person_id}`).replace(/[^a-zA-Z0-9_-]/g, '_');
  const blob = new Blob([gedContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${cleanName}_delmarva_lineage.ged`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
