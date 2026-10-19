/* Animated header mark shared by index.html and about.html:
   four coloured dots orbit and pass each other, then stretch into
   the four sides of a square. Loaded by both pages so the mark can
   never drift between them. */
(function () {
  var svg = document.getElementById("brand-logo-mark");
  if (!svg) return;

  var NS = "http://www.w3.org/2000/svg";
  var CX = 22;
  var CY = 22;
  var ORBIT_R = 15;
  var SIDE_LENGTH = 24;

  /* Square corners in draw order; each corner owns the side after it. */
  /* Coordinates live in a 44-unit frame. The inline SVG uses the viewBox
     "5 5 34 34", which frames the square (10-34) plus the orbit radius
     (15 units from the 22,22 centre), so nothing important is clipped. */
  var CORNERS = [
    [10, 10],
    [34, 10],
    [34, 34],
    [10, 34]
  ];
  /* yellow, lime, orange, blue (mirrors the CSS colour tokens). */
  var COLORS = ["#f2ff00", "#c2f345", "#ffa310", "#b9ffe7"];
  /* Different revolution counts make the dots overtake and pass. */
  var TURNS = [1, -1.25, 1.5, -0.75];

  /* Timeline fractions: orbit, settle, draw, hold, retract. */
  var ORBIT_END = 0.5;
  var MOVE_END = 0.62;
  var DRAW_END = 0.82;
  var HOLD_END = 0.92;
  var DURATION = 5200;

  var lines = [];
  var dots = [];
  var startAngle = [];

  CORNERS.forEach(function (corner, i) {
    var next = CORNERS[(i + 1) % 4];
    var line = document.createElementNS(NS, "line");
    line.setAttribute("x1", corner[0]);
    line.setAttribute("y1", corner[1]);
    line.setAttribute("x2", next[0]);
    line.setAttribute("y2", next[1]);
    line.setAttribute("stroke", COLORS[i]);
    line.setAttribute("stroke-width", "3.5");
    line.setAttribute("stroke-linecap", "round");
    line.setAttribute("stroke-dasharray", SIDE_LENGTH);
    line.setAttribute("stroke-dashoffset", SIDE_LENGTH);
    svg.appendChild(line);
    lines.push(line);

    startAngle.push(Math.atan2(corner[1] - CY, corner[0] - CX));
  });

  CORNERS.forEach(function (corner, i) {
    var dot = document.createElementNS(NS, "circle");
    dot.setAttribute("r", "3.2");
    dot.setAttribute("fill", COLORS[i]);
    svg.appendChild(dot);
    dots.push(dot);
  });

  function clamp01(value) {
    return Math.max(0, Math.min(1, value));
  }

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function orbitPosition(i, progress) {
    var angle = startAngle[i] + TURNS[i] * 2 * Math.PI * (clamp01(progress) / ORBIT_END);
    return [CX + ORBIT_R * Math.cos(angle), CY + ORBIT_R * Math.sin(angle)];
  }

  function render(p) {
    for (var i = 0; i < 4; i++) {
      var point;
      var offset;

      if (p <= ORBIT_END) {
        point = orbitPosition(i, p);
        offset = SIDE_LENGTH;
      } else if (p <= MOVE_END) {
        var k = easeInOutCubic((p - ORBIT_END) / (MOVE_END - ORBIT_END));
        var from = orbitPosition(i, ORBIT_END);
        point = [lerp(from[0], CORNERS[i][0], k), lerp(from[1], CORNERS[i][1], k)];
        offset = SIDE_LENGTH;
      } else if (p <= DRAW_END) {
        point = CORNERS[i];
        offset = SIDE_LENGTH * (1 - (p - MOVE_END) / (DRAW_END - MOVE_END));
      } else if (p <= HOLD_END) {
        point = CORNERS[i];
        offset = 0;
      } else {
        var back = easeInOutCubic((p - HOLD_END) / (1 - HOLD_END));
        var home = orbitPosition(i, 0);
        point = [lerp(CORNERS[i][0], home[0], back), lerp(CORNERS[i][1], home[1], back)];
        offset = SIDE_LENGTH * back;
      }

      dots[i].setAttribute("cx", point[0].toFixed(2));
      dots[i].setAttribute("cy", point[1].toFixed(2));
      lines[i].setAttribute("stroke-dashoffset", offset.toFixed(2));
    }
  }

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    render(HOLD_END);
    return;
  }

  var started = null;
  requestAnimationFrame(function loop(time) {
    if (started === null) started = time;
    render(((time - started) % DURATION) / DURATION);
    requestAnimationFrame(loop);
  });
})();
