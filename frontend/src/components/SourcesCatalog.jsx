import React, { useState } from 'react';
import { ExternalLink, Database, BookOpen, FileText, Search, ShieldCheck, HeartHandshake, Bookmark } from 'lucide-react';

export default function SourcesCatalog({ onOpenRecord }) {
  const [filterQuery, setFilterQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const mainRepositories = [
    {
      name: 'Mitsawokett Delaware Native Archive',
      domain: 'nativeamericansofdelawarestate.com',
      url: 'https://nativeamericansofdelawarestate.com/MainMenu.html',
      wayback: 'https://web.archive.org/web/20160403/https://nativeamericansofdelawarestate.com',
      badge: '1,948 Photos • 364 Obituaries • 1,023 Persons',
      color: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
      description: 'Primary repository for Nanticoke & Moor history in Kent & Sussex Counties, Delaware. Features all 28 Photographic Survey tabs, family Bibles, probate wills, and census records.'
    },
    {
      name: 'Lynn C. Jackson Family Archive',
      domain: 'lynncjackson.com',
      url: 'https://lynncjackson.com',
      wayback: 'https://web.archive.org/web/2018/https://lynncjackson.com',
      badge: '729 Preserved Persons',
      color: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
      description: 'Comprehensive family tree, census extraction, and oral history archive of the Jackson, Durham, Harmon, and Mosley families.'
    },
    {
      name: 'The Moors of Delaware Database',
      domain: 'moors-delaware.com',
      url: 'http://www.moors-delaware.com/gendat/moors.aspx',
      wayback: 'https://web.archive.org/web/2016/http://www.moors-delaware.com',
      badge: '101 Cataloged Persons',
      color: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
      description: 'Joseph Romeo’s historical genealogical database tracking Delaware Moor families, land deeds, and vital statistic records.'
    },
    {
      name: 'Smithsonian NMAI Frank G. Speck Collection',
      domain: 'americanindian.si.edu',
      url: 'https://americanindian.si.edu/collections-search/search/archives',
      wayback: 'https://sova.si.edu/details/NMAI.AC.001.008',
      badge: 'Series 8: Delaware Nanticoke',
      color: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
      description: 'National Museum of the American Indian Archives Center collection (NMAI.AC.001.008) containing Frank Speck’s 1911–1920 field photographs and Nanticoke elder portraits.'
    },
    {
      name: 'Native American Roots — Frank Speck Series',
      domain: 'nativeamericanroots.wordpress.com',
      url: 'https://nativeamericanroots.wordpress.com/tag/frank-speck/',
      wayback: 'https://nativeamericanroots.wordpress.com/2016/03/01/elias-bookram-a-nanticoke-indian-from-maryland-in-granville-county/',
      badge: 'Puckham / Bookram Lineage',
      color: 'border-rose-500/40 bg-rose-500/10 text-rose-300',
      description: 'Ethnographic and genealogical analysis documenting the John Puckham (b.1660) and Elias Bookram (b.1790) Nanticoke lineage evolution.'
    },
    {
      name: 'Wikipedia: Nanticoke People Historical Monograph',
      domain: 'en.wikipedia.org',
      url: 'https://en.wikipedia.org/wiki/Nanticoke_people',
      wayback: 'https://web.archive.org/web/2026/https://en.wikipedia.org/wiki/Nanticoke_people',
      badge: 'Ethnographic & Tribal History',
      color: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
      description: 'Authoritative encyclopedic history of the Nanticoke people, tidewater Algonquian origins (Nentego), 1742 Winnesoccum treaty, migrations to Six Nations Ontario & Oklahoma, and state-recognized tribal communities in Delaware and New Jersey.'
    },
    {
      name: 'SaponiTown: Eastern Nanticoke-Lenape/Saponi Forum',
      domain: 'saponitown.com',
      url: 'https://saponitown.com/forums/topic/eastern-nanticoke-lenapesaponi/',
      wayback: 'https://web.archive.org/web/2026/https://saponitown.com/forums/topic/eastern-nanticoke-lenapesaponi/',
      badge: 'Delmarva & Blackfoot Town Research',
      color: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
      description: 'Genealogical research forum documenting Eastern Shore MD & Sussex County DE family enclaves (Jackson Town in Marumsco, Holden Creek, Dagsboro Blackfoot Town), and family names (Jackson, Collins, Bell, Selby, Green, Holden, Lane, Stewart, Williams).'
    },
    {
      name: 'Delaware’s Invisible Indians (Heite Consulting Monograph)',
      domain: 'nativeamericansofdelawarestate.com',
      url: 'https://nativeamericansofdelawarestate.com/HeiteReport1.htm',
      wayback: 'https://web.archive.org/web/2016/https://nativeamericansofdelawarestate.com/HeiteReport1.htm',
      badge: '17th–18th C. Archaeological & Deed Survey',
      color: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
      description: 'Dr. Louise Heite & Edward Heite monograph detailing 17th-century Mitsawokett land sales by Chief Petticoquewan (Christian), Jolley’s Neck Handsor landholdings, cultural invisibility survival strategies, and probate cross-sections of Kent County families.'
    }
  ];

  const primaryDocuments = [
    {
      category: 'censuses',
      title: 'Delaware Change of Race Document (1930 Census Reclassification)',
      filename: 'Change_of_Race.htm',
      url: 'https://nativeamericansofdelawarestate.com/Change_of_Race.htm',
      wayback: 'https://web.archive.org/web/20160403/https://nativeamericansofdelawarestate.com/Change_of_Race.htm',
      description: 'Legal & census analysis documenting how 1930 Federal Census enumerators wrote "Indian Mixed Nanticoke" or "Delaware Nanticoke Tribe" but supervisors altered race codes from "In" to "Neg". Includes 1711 Indian River reservation land deeds for Wassason and Queen Weatomotonies.'
    },
    {
      category: 'censuses',
      title: 'The Winnesoccum Disaster (1742 Peace Treaty)',
      filename: 'Winnesoccum.htm',
      url: 'https://nativeamericansofdelawarestate.com/Winnesoccum.htm',
      wayback: 'https://web.archive.org/web/20160403/https://nativeamericansofdelawarestate.com/Winnesoccum.htm',
      description: 'Colonial treaty record of the 1742 Winnasoccum meeting between Eastern Shore tribes and the Shawnee, signed by Nanticoke Chief George Puckham.'
    },
    {
      category: 'bibles',
      title: 'Perkins-Adams-Morris-Jackson Family Bible',
      filename: 'Bible Records/Perkins-Adams-Morris-JacksonBible.htm',
      url: 'https://nativeamericansofdelawarestate.com/Bible%20Records/Perkins-Adams-Morris-JacksonBible.htm',
      description: 'Preserved Bible family register from Sussex County, DE documenting births, marriages, and deaths.'
    },
    {
      category: 'bibles',
      title: 'Emily C. Johnson Wright Family Bible',
      filename: 'Bible Records/EmilyCJohnsonWrightBible.htm',
      url: 'https://nativeamericansofdelawarestate.com/Bible%20Records/EmilyCJohnsonWrightBible.htm',
      description: 'Preserved family register of the Wright and Johnson lineages in Kent and Sussex Counties.'
    },
    {
      category: 'bibles',
      title: 'James & Harriet (Cork) Greenage Family Bible',
      filename: 'Bible Records/GreenageJames&HarriettBible.htm',
      url: 'https://nativeamericansofdelawarestate.com/Bible%20Records/GreenageJames&HarriettBible.htm',
      description: 'Family register documenting the Greenage and Cork families of Cheswold, DE.'
    },
    {
      category: 'bibles',
      title: 'Maymie Beckett Durham Family Bible',
      filename: 'Bible Records/MAYMIE_DURHAM_BIBLE.htm',
      url: 'https://nativeamericansofdelawarestate.com/Bible%20Records/MAYMIE_DURHAM_BIBLE.htm',
      description: 'Family record register of the Durham and Beckett lineages in Kent County.'
    },
    {
      category: 'probates',
      title: 'George Durham Will & Estate Records (1844)',
      filename: 'George Durham Will 1844.htm',
      url: 'https://nativeamericansofdelawarestate.com/George%20Durham%20Will%201844.htm',
      description: '1844 Kent County will and land partition document of George Durham.'
    },
    {
      category: 'probates',
      title: 'Elijah Consellor Lineage & Probate Records (1811/1845)',
      filename: 'Consellor Lineage.htm',
      url: 'https://nativeamericansofdelawarestate.com/Consellor%20Lineage.htm',
      description: 'Lineage chart and estate records of Elijah Counselor (Consellor) of Cheswold.'
    },
    {
      category: 'probates',
      title: 'Emmanuel Harmon Estate & Land Records',
      filename: 'HarmonEmmanuelProbate.htm',
      url: 'https://nativeamericansofdelawarestate.com/HarmonEmmanuelProbate.htm',
      description: 'Probate files and land deeds of Emmanuel Harmon in Sussex County.'
    },
    {
      category: 'indentures',
      title: 'Warren Wright Children Apprentice Indentures (1843)',
      filename: 'Apprenticeships/WarrenWrightsChildren/Apprentice Indentures - Warren Wright family 1843.htm',
      url: 'https://nativeamericansofdelawarestate.com/Apprenticeships/WarrenWrightsChildren/Apprentice%20Indentures%20-%20Warren%20Wright%20family%201843.htm',
      description: '1843 Sussex County apprenticeship binding records of Warren Wright’s children.'
    },
    {
      category: 'indentures',
      title: 'Samuel Loatman Apprenticeship Indenture (1839)',
      filename: 'Apprenticeships/Samuel Loatman/Samuel Loatman Apprenticeship.htm',
      url: 'https://nativeamericansofdelawarestate.com/Apprenticeships/Samuel%20Loatman/Samuel%20Loatman%20Apprenticeship.htm',
      description: '1839 Kent County apprenticeship indenture of Samuel Loatman (1826–1903).'
    },
    {
      category: 'essays',
      title: 'The Durhams of Kent County Delaware',
      filename: 'DurhamsOfKentCoDE.htm',
      url: 'https://nativeamericansofdelawarestate.com/DurhamsOfKentCoDE.htm',
      description: 'Historical monograph on the Durham family origins in Kent County by Harry Muncey.'
    },
    {
      category: 'essays',
      title: 'Cheswold Origins by JoAnne Sammons',
      filename: 'Cheswold origins by Joann Sammons.htm',
      url: 'https://nativeamericansofdelawarestate.com/Cheswold%20origins%20by%20Joann%20Sammons.htm',
      description: 'Historical narrative on the founding families of Cheswold, Kent County.'
    }
  ];

  const filteredDocs = primaryDocuments.filter(doc => {
    const matchesCat = selectedCategory === 'all' || doc.category === selectedCategory;
    const matchesQuery = filterQuery === '' || 
      doc.title.toLowerCase().includes(filterQuery.toLowerCase()) || 
      doc.description.toLowerCase().includes(filterQuery.toLowerCase());
    return matchesCat && matchesQuery;
  });

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Section Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bookmark className="w-6 h-6 text-amber-400" /> Preserved Sources & Citation Index
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Complete list of all integrated digital archives, primary court records, Bibles, censuses, and Wayback Machine citations.
          </p>
        </div>
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search sources or records..."
            value={filterQuery}
            onChange={e => setFilterQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
          />
        </div>
      </div>

      {/* Main Integrated Repositories */}
      <div>
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Database className="w-4 h-4 text-amber-400" /> Integrated Digital Repositories
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {mainRepositories.map((repo, idx) => (
            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-amber-500/40 transition-all flex flex-col justify-between shadow-lg">
              <div>
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[11px] font-mono px-2.5 py-0.5 rounded border ${repo.color}`}>
                    {repo.badge}
                  </span>
                </div>
                <h4 className="text-base font-bold text-slate-100 mt-2">{repo.name}</h4>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{repo.description}</p>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono">
                <a
                  href={repo.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-amber-400 hover:text-amber-300 flex items-center gap-1 font-medium"
                >
                  Direct Link <ExternalLink className="w-3 h-3" />
                </a>
                {repo.wayback && (
                  <a
                    href={repo.wayback}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sky-400 hover:text-sky-300 flex items-center gap-1 text-[11px]"
                  >
                    Wayback <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Primary Historical Documents Section */}
      <div>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <FileText className="w-4 h-4 text-sky-400" /> Preserved Primary Documents & Bibles
          </h3>
          {/* Category Filter Chips */}
          <div className="flex flex-wrap gap-2 text-xs">
            {[
              { id: 'all', label: 'All Documents' },
              { id: 'censuses', label: 'Censuses & Treaties' },
              { id: 'bibles', label: 'Family Bibles' },
              { id: 'probates', label: 'Wills & Probates' },
              { id: 'indentures', label: 'Apprenticeships' },
              { id: 'essays', label: 'Historical Essays' }
            ].map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  selectedCategory === cat.id
                    ? 'bg-amber-500 text-slate-950 font-bold shadow-md'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredDocs.map((doc, idx) => (
            <div
              key={idx}
              className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 hover:border-sky-500/40 transition-all flex flex-col justify-between shadow-md"
            >
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-[10px] font-mono uppercase text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded">
                    {doc.category}
                  </span>
                  <button
                    onClick={() => onOpenRecord(doc.filename)}
                    className="text-xs text-amber-400 hover:text-amber-300 font-medium"
                  >
                    Preview in App →
                  </button>
                </div>
                <h4 className="text-sm font-bold text-slate-200 mt-1">{doc.title}</h4>
                <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{doc.description}</p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono">
                <a
                  href={doc.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-300 hover:text-amber-300 flex items-center gap-1 truncate max-w-[70%]"
                >
                  <ExternalLink className="w-3 h-3 shrink-0" />
                  <span className="truncate">{doc.url}</span>
                </a>
                {doc.wayback && (
                  <a
                    href={doc.wayback}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sky-400 hover:text-sky-300 font-medium shrink-0 ml-2"
                  >
                    Wayback
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
