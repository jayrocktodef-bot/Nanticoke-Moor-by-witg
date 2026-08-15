import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function FanChart({ ancestryData, onSelectPerson }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!ancestryData || !svgRef.current) return;

    // Clear previous render
    d3.select(svgRef.current).selectAll("*").remove();

    const width = 800;
    const radius = width / 2;

    const svg = d3.select(svgRef.current)
      .attr("viewBox", [-width / 2, -radius, width, radius + 20])
      .style("font", "10px sans-serif")
      .style("width", "100%")
      .style("height", "auto")
      .style("max-width", "100%");

    // Hierarchy and value sorting
    const root = d3.hierarchy(ancestryData);
    
    // Each leaf gets a value of 1 so parents aggregate up (equal slices)
    root.count();

    // Partition layout for a half circle (Math.PI)
    const partition = d3.partition()
      .size([Math.PI, radius]);

    partition(root);

    // Color scale based on depth
    const color = d3.scaleOrdinal(d3.quantize(d3.interpolateRainbow, root.height + 1));

    // Arc generator shifted by -90 degrees (-Math.PI/2) to span from 9 o'clock to 3 o'clock
    const arc = d3.arc()
      .startAngle(d => d.x0 - Math.PI / 2)
      .endAngle(d => d.x1 - Math.PI / 2)
      .padAngle(0.005)
      .padRadius(radius / 2)
      .innerRadius(d => d.y0)
      .outerRadius(d => d.y1 - 1);

    const cell = svg.selectAll("g")
      .data(root.descendants())
      .join("g");

    // Draw the slices
    cell.append("path")
      .attr("d", arc)
      .attr("fill", d => color(d.depth))
      .attr("fill-opacity", 0.8)
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        if (d.data.id && onSelectPerson) {
          onSelectPerson(d.data.id);
        }
      })
      .on("mouseover", function() { d3.select(this).attr("fill-opacity", 1); })
      .on("mouseout", function() { d3.select(this).attr("fill-opacity", 0.8); })
      .append("title")
      .text(d => `${d.data.name} (ID: ${d.data.id})`);

    // Add labels
    cell.append("text")
      .attr("transform", d => {
        // x is the angle from 12 o'clock, ranging from -Math.PI/2 to Math.PI/2
        const x = (d.x0 + d.x1) / 2 - Math.PI / 2;
        const y = (d.y0 + d.y1) / 2;
        // D3 angles start at 12 o'clock and go clockwise.
        // SVG rotate angles start at 3 o'clock and go clockwise.
        // So angle in SVG degrees = x * 180 / Math.PI - 90
        const angleSvg = (x * 180 / Math.PI) - 90;
        
        // If it's on the left side, flip the text so it's upright
        const rotateText = (angleSvg < -90 || angleSvg > 90) ? 180 : 0;
        
        return `rotate(${angleSvg}) translate(${y},0) rotate(${rotateText})`;
      })
      .attr("dy", "0.35em")
      // Adjust text anchor based on which side of the fan it is
      .attr("text-anchor", d => {
        const x = (d.x0 + d.x1) / 2 - Math.PI / 2;
        const angleSvg = (x * 180 / Math.PI) - 90;
        return (angleSvg < -90 || angleSvg > 90) ? "end" : "start";
      })
      .attr("dx", d => {
        const x = (d.x0 + d.x1) / 2 - Math.PI / 2;
        const angleSvg = (x * 180 / Math.PI) - 90;
        return (angleSvg < -90 || angleSvg > 90) ? "-5px" : "5px";
      })
      .style("fill", "#fff")
      .style("font-size", "11px")
      .style("font-weight", "500")
      .style("pointer-events", "none")
      .text(d => {
        // Don't show text if the slice is too thin
        if ((d.x1 - d.x0) < 0.05 && d.depth > 3) return "";
        return d.data.name ? d.data.name.substring(0, 20) : "";
      });

  }, [ancestryData, onSelectPerson]);

  return (
    <div className="w-full flex justify-center py-6 bg-slate-900 rounded-xl mt-4 overflow-hidden border border-slate-700 shadow-inner">
      {ancestryData ? (
        <svg ref={svgRef}></svg>
      ) : (
        <div className="text-slate-500 italic py-10">No ancestry data available.</div>
      )}
    </div>
  );
}
