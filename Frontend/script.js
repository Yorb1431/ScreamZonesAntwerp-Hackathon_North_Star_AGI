// script.js

// Initialize the map
const map = L.map('map').setView([51.2194, 4.4025], 13); // Antwerp center

// Load and display tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Example scream zones (you can replace with actual GeoJSON data later)
const screamZones = [
  {
    name: 'Rivierenhof Park',
    coords: [51.2223, 4.4609],
    type: 'forest',
    score: '🔊🔊🔊🔊🔊',
    description: 'Great echo, peaceful, nature-approved scream zone.'
  },
  {
    name: 'Stadspark Tunnel',
    coords: [51.2139, 4.4162],
    type: 'tunnel',
    score: '🔊🔊🔊🔊',
    description: 'Decent echo and semi-hidden. Slightly sketchy.'
  },
  {
    name: 'Groenplaats',
    coords: [51.2182, 4.4007],
    type: 'square',
    score: '🔇',
    description: 'Too crowded. Someone will call the cops.'
  },
  {
    name: 'MAS Dockside',
    coords: [51.2289, 4.4047],
    type: 'river',
    score: '🔊🔊🔊',
    description: 'Open space, wind carries the scream. Melancholic vibes.'
  }
];

// Define marker styles by type
const icons = {
  forest: 'green',
  tunnel: 'gray',
  square: 'red',
  river: 'blue'
};

screamZones.forEach((zone) => {
  const marker = L.circleMarker(zone.coords, {
    radius: 10,
    color: icons[zone.type] || 'white',
    fillColor: icons[zone.type] || 'white',
    fillOpacity: 0.7
  }).addTo(map);

  marker.bindPopup(
    `<strong>${zone.name}</strong><br/>` +
    `${zone.description}<br/>` +
    `<span class="text-sm">Scream Score: ${zone.score}</span>`
  );
});