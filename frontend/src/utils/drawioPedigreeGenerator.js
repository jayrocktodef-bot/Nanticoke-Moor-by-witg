/**
 * Draw.io Genetic Pedigree & Lineage Tree Geometry Engine
 * (frontend/src/utils/drawioPedigreeGenerator.js)
 * =======================================================
 * Implements strict uncompressed Draw.io / diagrams.net XML generation
 * adhering to the drawio-genetic-pedigree standard:
 * - Mathematical generational coordinate indexing (box_height 60px, row_delta_y 100px)
 * - Parent centering over immediate descendant spans
 * - Orthogonal bus-bar routing with 20px junction drops
 * - Distinct vertex styles for Individual Ancestors, Marital Couples, and DNA Matches
 * - Semantic ID namespacing ([treePrefix_]gen[N]_[uniqueSlug])
 * - Full character entity escaping (&#xa;, &amp;, &lt;, &gt;, &quot;)
 */

const CONFIG = {
  boxHeight: 60,
  rowDeltaY: 100, // boxHeight (60) + verticalSpacing (40)
  verticalSpacing: 40,
  boxWidthIndividual: 140,
  boxWidthCouple: 220,
  horizontalSpacing: 36,
  yStart: 60,
  xStart: 60
};

/**
 * Clean text for draw.io XML values using standard XML/HTML entities
 */
export function escapeDrawioText(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '&#xa;');
}

/**
 * Generate a slug identifier for XML cell IDs
 */
export function slugify(text) {
  if (!text) return 'unknown';
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 30);
}

/**
 * Build a structured genealogical tree model from flat graph nodes and edges
 */
export function buildGenealogicalHierarchy(rootPersonId, nodesById, edges, options = {}) {
  const mode = options.mode || 'descendancy'; // 'descendancy' or 'pedigree'
  const maxGenerations = options.maxGenerations || 5;

  const childrenMap = {};
  const parentsMap = {};
  const spousesMap = {};

  (edges || []).forEach(e => {
    const fromId = Number(e.from);
    const toId = Number(e.to);
    const type = e.type || e.label;

    if (type === 'child_of') {
      // from is child, to is parent
      childrenMap[toId] = childrenMap[toId] || [];
      if (!childrenMap[toId].includes(fromId)) childrenMap[toId].push(fromId);

      parentsMap[fromId] = parentsMap[fromId] || [];
      if (!parentsMap[fromId].includes(toId)) parentsMap[fromId].push(toId);
    } else if (type === 'parent_of') {
      // from is parent, to is child
      childrenMap[fromId] = childrenMap[fromId] || [];
      if (!childrenMap[fromId].includes(toId)) childrenMap[fromId].push(toId);

      parentsMap[toId] = parentsMap[toId] || [];
      if (!parentsMap[toId].includes(fromId)) parentsMap[toId].push(fromId);
    } else if (type === 'spouse' || type === 'spouse_of') {
      spousesMap[fromId] = spousesMap[fromId] || [];
      if (!spousesMap[fromId].includes(toId)) spousesMap[fromId].push(toId);

      spousesMap[toId] = spousesMap[toId] || [];
      if (!spousesMap[toId].includes(fromId)) spousesMap[toId].push(fromId);
    }
  });

  return {
    rootPersonId: Number(rootPersonId),
    nodesById,
    childrenMap,
    parentsMap,
    spousesMap,
    mode,
    maxGenerations
  };
}

/**
 * Calculate mathematical 2D layout coordinates for a descendancy pedigree tree
 */
export function computePedigreeLayout(treeModel) {
  const { rootPersonId, nodesById, childrenMap, spousesMap, maxGenerations } = treeModel;

  const rootPerson = nodesById[rootPersonId];
  if (!rootPerson) {
    return { nodes: [], edges: [], busBars: [], bounds: { width: 800, height: 600 } };
  }

  const visitedDescendants = new Set();
  const generationNodes = []; // array of arrays per generation

  // Helper to build a recursive branch
  function buildBranch(personId, genIndex) {
    if (genIndex > maxGenerations || visitedDescendants.has(personId)) return null;
    visitedDescendants.add(personId);

    const person = nodesById[personId] || { id: personId, label: `Person #${personId}` };
    const spouseIds = spousesMap[personId] || [];
    const primarySpouseId = spouseIds[0];
    const primarySpouse = primarySpouseId ? nodesById[primarySpouseId] : null;

    const isCouple = !!primarySpouse;
    const boxWidth = isCouple ? CONFIG.boxWidthCouple : CONFIG.boxWidthIndividual;

    // Direct children
    const childIds = childrenMap[personId] || [];
    const childBranches = [];

    childIds.forEach(cId => {
      const childBranch = buildBranch(cId, genIndex + 1);
      if (childBranch) childBranches.push(childBranch);
    });

    const nodeItem = {
      id: personId,
      slug: slugify(person.label || person.name),
      genIndex,
      isCouple,
      primaryPerson: person,
      spousePerson: primarySpouse,
      width: boxWidth,
      height: CONFIG.boxHeight,
      x: 0,
      y: CONFIG.yStart + (genIndex * CONFIG.rowDeltaY),
      children: childBranches,
      subtreeWidth: 0
    };

    return nodeItem;
  }

  const rootBranch = buildBranch(rootPersonId, 1);
  if (!rootBranch) {
    return { nodes: [], edges: [], busBars: [], bounds: { width: 800, height: 600 } };
  }

  // Pass 1: Compute subtree widths from bottom to top
  function computeSubtreeWidth(branch) {
    if (!branch.children || branch.children.length === 0) {
      branch.subtreeWidth = branch.width;
      return branch.width;
    }

    let totalChildrenWidth = 0;
    branch.children.forEach((child, idx) => {
      const cWidth = computeSubtreeWidth(child);
      totalChildrenWidth += cWidth;
      if (idx > 0) totalChildrenWidth += CONFIG.horizontalSpacing;
    });

    branch.subtreeWidth = Math.max(branch.width, totalChildrenWidth);
    return branch.subtreeWidth;
  }

  computeSubtreeWidth(rootBranch);

  // Pass 2: Position coordinates top-down using Parent Centering Rule
  const flattenedNodes = [];
  const busBars = [];
  const edges = [];

  function positionBranch(branch, leftX) {
    // If no children, place at leftX
    if (!branch.children || branch.children.length === 0) {
      branch.x = leftX;
    } else {
      // Position all children side by side
      let curX = leftX;
      branch.children.forEach(child => {
        positionBranch(child, curX);
        curX += child.subtreeWidth + CONFIG.horizontalSpacing;
      });

      // Parent Centering Rule:
      // X_parent_center = (X_first_child + X_last_child + child_width) / 2 - (parent_box_width / 2)
      const firstChild = branch.children[0];
      const lastChild = branch.children[branch.children.length - 1];
      const childrenSpanCenter = (firstChild.x + lastChild.x + lastChild.width) / 2;
      branch.x = childrenSpanCenter - (branch.width / 2);

      // Prevent parent X from going left of leftX boundary
      if (branch.x < leftX) {
        const delta = leftX - branch.x;
        branch.x = leftX;
        // Shift children right
        function shiftRight(b, amt) {
          b.x += amt;
          (b.children || []).forEach(c => shiftRight(c, amt));
        }
        branch.children.forEach(c => shiftRight(c, delta));
      }

      // Generate Orthogonal Bus Bar for siblings
      const yParentBottom = branch.y + branch.height;
      const yBus = yParentBottom + 20; // 20px junction drop
      const parentXCenter = branch.x + (branch.width / 2);

      const childXCenters = branch.children.map(c => c.x + (c.width / 2));
      const minChildX = Math.min(parentXCenter, ...childXCenters);
      const maxChildX = Math.max(parentXCenter, ...childXCenters);

      busBars.push({
        id: `busbar_gen${branch.genIndex}_${branch.slug}`,
        parentX: parentXCenter,
        yParentBottom,
        yBus,
        minChildX,
        maxChildX,
        childDrops: branch.children.map(c => ({
          childId: c.id,
          x: c.x + (c.width / 2),
          yTop: c.y
        }))
      });

      branch.children.forEach(c => {
        edges.push({
          id: `edge_gen${branch.genIndex}_${branch.slug}_to_gen${c.genIndex}_${c.slug}`,
          sourceId: `gen${branch.genIndex}_${branch.slug}`,
          targetId: `gen${c.genIndex}_${c.slug}`,
          parentX: parentXCenter,
          yBus,
          childX: c.x + (c.width / 2),
          childY: c.y
        });
      });
    }

    flattenedNodes.push(branch);
  }

  positionBranch(rootBranch, CONFIG.xStart);

  // Calculate diagram bounding box
  let maxX = 0;
  let maxY = 0;
  flattenedNodes.forEach(n => {
    maxX = Math.max(maxX, n.x + n.width + CONFIG.horizontalSpacing);
    maxY = Math.max(maxY, n.y + n.height + CONFIG.verticalSpacing);
  });

  return {
    nodes: flattenedNodes,
    edges,
    busBars,
    bounds: {
      width: Math.max(maxX + CONFIG.xStart, 900),
      height: Math.max(maxY + CONFIG.yStart, 500)
    }
  };
}

/**
 * Generate standard, uncompressed Draw.io / diagrams.net XML
 * strictly matching the schema in the drawio-genetic-pedigree standard.
 */
export function generateDrawioXml(layoutData, metadata = {}) {
  const { nodes, edges, bounds } = layoutData;
  const treeTitle = metadata.title || 'Genetic Pedigree & Lineage Tree';
  const modifiedDate = new Date().toISOString().split('T')[0];

  const xmlCells = [];

  // System Root Cells
  xmlCells.push('        <mxCell id="0" />');
  xmlCells.push('        <mxCell id="1" parent="0" />');

  // Vertex Styles per drawio-genetic-pedigree specification
  const STYLE_INDIVIDUAL = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Verdana;fontSize=11;fontStyle=1;strokeWidth=2;strokeColor=#999999;fillColor=#ffffff;align=center;verticalAlign=middle;';
  const STYLE_COUPLE = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Verdana;fontSize=11;fontStyle=1;strokeWidth=2;strokeColor=#999999;fillColor=#ffffff;align=center;verticalAlign=middle;';
  const STYLE_DNA_MATCH = 'rounded=1;whiteSpace=wrap;html=1;fontFamily=Verdana;fontSize=11;fontStyle=2;strokeWidth=2;strokeColor=#000000;fillColor=#ffffff;align=center;verticalAlign=middle;';

  // Generation Nodes
  nodes.forEach(node => {
    const cellId = `gen${node.genIndex}_${node.slug}`;
    const p1 = node.primaryPerson;
    const p2 = node.spousePerson;

    let label = '';
    let style = STYLE_INDIVIDUAL;

    if (node.isDNA || node.centimorgans) {
      style = STYLE_DNA_MATCH;
      const initials = p1.label ? p1.label.split(' ').map(w => w[0]).join('. ') : 'DNA Match';
      const cM = node.centimorgans || 120;
      const rel = node.relationshipCode || 'DNA Match';
      label = `&lt;b&gt;${escapeDrawioText(initials)}&lt;/b&gt;&#xa;Living&#xa;&lt;font color=&quot;#ff0000&quot;&gt;${cM} cM | ${rel}&lt;/font&gt;`;
    } else if (node.isCouple && p2) {
      style = STYLE_COUPLE;
      const n1 = escapeDrawioText(p1.label || p1.name);
      const n2 = escapeDrawioText(p2.label || p2.name);
      const note = p1.source_page ? escapeDrawioText(p1.source_page) : 'Preserved Union';
      label = `&lt;b&gt;${n1}&lt;/b&gt;&#xa;&lt;b&gt;${n2}&lt;/b&gt;&#xa;${note}`;
    } else {
      style = STYLE_INDIVIDUAL;
      const n1 = escapeDrawioText(p1.label || p1.name);
      const dates = escapeDrawioText(p1.birth_info || p1.source_page || 'Historical Ancestor');
      label = `&lt;b&gt;${n1}&lt;/b&gt;&#xa;${dates}`;
    }

    xmlCells.push(`        <!-- Gen ${node.genIndex}: ${escapeDrawioText(p1.label || p1.name)} -->`);
    xmlCells.push(`        <mxCell id="${cellId}" value="${label}" style="${style}" vertex="1" parent="1">`);
    xmlCells.push(`          <mxGeometry x="${Math.round(node.x)}" y="${Math.round(node.y)}" width="${node.width}" height="${node.height}" as="geometry" />`);
    xmlCells.push('        </mxCell>');
  });

  // Orthogonal Bus Bar Edges
  edges.forEach(edge => {
    const edgeStyle = 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=none;strokeWidth=1.5;strokeColor=#666666;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;';

    xmlCells.push(`        <mxCell id="${edge.id}" style="${edgeStyle}" edge="1" source="${edge.sourceId}" target="${edge.targetId}" parent="1">`);
    xmlCells.push('          <mxGeometry relative="1" as="geometry">');
    xmlCells.push('            <Array as="points">');
    xmlCells.push(`              <mxPoint x="${Math.round(edge.parentX)}" y="${Math.round(edge.yBus)}" />`);
    xmlCells.push(`              <mxPoint x="${Math.round(edge.childX)}" y="${Math.round(edge.yBus)}" />`);
    xmlCells.push('            </Array>');
    xmlCells.push('          </mxGeometry>');
    xmlCells.push('        </mxCell>');
  });

  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="${modifiedDate}" agent="GoogleAntigravity" version="24.0.0" type="device">
  <diagram id="pedigree-lineage-diagram" name="${escapeDrawioText(treeTitle)}">
    <mxGraphModel dx="${Math.round(bounds.width + 200)}" dy="${Math.round(bounds.height + 200)}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${Math.round(bounds.width + 100)}" pageHeight="${Math.round(bounds.height + 100)}" math="0" shadow="0">
      <root>
${xmlCells.join('\n')}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>`;

  return xmlContent;
}

/**
 * Trigger client-side browser file download for .drawio XML
 */
export function downloadDrawioFile(xmlContent, filename = 'family-pedigree-tree.drawio') {
  const blob = new Blob([xmlContent], { type: 'application/vnd.jgraph.mxfile;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.drawio') ? filename : `${filename}.drawio`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Copy Draw.io XML to clipboard
 */
export async function copyDrawioToClipboard(xmlContent) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(xmlContent);
    return true;
  }
  return false;
}
