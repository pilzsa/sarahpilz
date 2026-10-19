/* Hero for index.html: D3 light beams behind a React-rendered typing line.
   A classic script (not an ES module) so the page also works when opened
   straight from the filesystem. index.html must load react, react-dom and d3
   first -- see the CDN <script> tags at the bottom of the page. */
(function () {
  var h = React.createElement;
  var useState = React.useState;
  var useEffect = React.useEffect;
  var useRef = React.useRef;

  /* Beam colours mirror the CSS colour tokens in :root. */
  var BEAMS = [
    { key: "yellow", color: "#f2ff00", width: 120, baseX: 0.18, speed: 0.24, phase: 0.0, angle: -16, range: 70, opacity: 0.55 },
    { key: "lime", color: "#c2f345", width: 90, baseX: 0.42, speed: 0.18, phase: 1.7, angle: 10, range: 55, opacity: 0.5 },
    { key: "orange", color: "#ffa310", width: 130, baseX: 0.68, speed: 0.21, phase: 3.1, angle: -6, range: 80, opacity: 0.5 },
    { key: "blue", color: "#b9ffe7", width: 160, baseX: 0.9, speed: 0.15, phase: 4.6, angle: 18, range: 60, opacity: 0.6 }
  ];

  var VIEW_W = 1000;
  var VIEW_H = 600;
  var BEAM_HEIGHT = 1800;
  var HERO_TEXT = "Research. Data. Science. Collaboration.";

  function BeamBackground() {
    var svgRef = useRef(null);

    useEffect(function () {
      var svg = d3.select(svgRef.current);
      var defs = svg.append("defs");

      defs.append("filter")
        .attr("id", "beam-blur")
        .attr("x", "-60%")
        .attr("y", "-60%")
        .attr("width", "220%")
        .attr("height", "220%")
        .append("feGaussianBlur")
        .attr("stdDeviation", 48);

      BEAMS.forEach(function (beam) {
        var gradient = defs.append("linearGradient")
          .attr("id", "beam-" + beam.key)
          .attr("x1", "0%")
          .attr("y1", "0%")
          .attr("x2", "100%")
          .attr("y2", "0%");
        gradient.append("stop").attr("offset", "0%").attr("stop-color", beam.color).attr("stop-opacity", 0);
        gradient.append("stop").attr("offset", "50%").attr("stop-color", beam.color).attr("stop-opacity", 1);
        gradient.append("stop").attr("offset", "100%").attr("stop-color", beam.color).attr("stop-opacity", 0);
      });

      var nodes = svg.append("g")
        .attr("class", "beam-layer")
        .selectAll("rect")
        .data(BEAMS, function (d) { return d.key; })
        .join("rect")
        .attr("x", function (d) { return -d.width / 2; })
        .attr("y", -BEAM_HEIGHT / 2)
        .attr("width", function (d) { return d.width; })
        .attr("height", BEAM_HEIGHT)
        .attr("fill", function (d) { return "url(#beam-" + d.key + ")"; })
        .attr("filter", "url(#beam-blur)")
        .attr("opacity", function (d) { return d.opacity; })
        .nodes();

      function place(i, elapsed) {
        var beam = BEAMS[i];
        var t = elapsed / 1000;
        var x = beam.baseX * VIEW_W + Math.sin(t * beam.speed + beam.phase) * beam.range;
        var y = VIEW_H / 2 + Math.cos(t * beam.speed * 0.6 + beam.phase) * 60;
        var rotate = beam.angle + Math.sin(t * beam.speed * 0.45 + beam.phase) * 7;
        nodes[i].setAttribute(
          "transform",
          "translate(" + x.toFixed(1) + " " + y.toFixed(1) + ") rotate(" + rotate.toFixed(2) + ")"
        );
      }

      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        BEAMS.forEach(function (beam, i) { place(i, 0); });
        return function () { svg.selectAll("*").remove(); };
      }

      var timer = d3.timer(function (elapsed) {
        BEAMS.forEach(function (beam, i) { place(i, elapsed); });
      });

      return function () {
        timer.stop();
        svg.selectAll("*").remove();
      };
    }, []);

    return h("svg", {
      ref: svgRef,
      className: "hero-beams",
      viewBox: "0 0 " + VIEW_W + " " + VIEW_H,
      preserveAspectRatio: "xMidYMid slice",
      "aria-hidden": "true"
    });
  }

  function TypingLine() {
    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var state = useState(0);
    var count = state[0];
    var setCount = state[1];

    useEffect(function () {
      if (reduced || count >= HERO_TEXT.length) return undefined;
      var id = window.setTimeout(function () { setCount(count + 1); }, 85);
      return function () { window.clearTimeout(id); };
    }, [count, reduced]);

    var typed = reduced ? HERO_TEXT : HERO_TEXT.slice(0, count);

    return h(
      "h1",
      { className: "hero-title", id: "hero-title" },
      h("span", { "aria-hidden": "true" }, typed, h("span", { className: "hero-caret" })),
      h("span", { className: "visually-hidden" }, HERO_TEXT)
    );
  }

  function Hero() {
    return h(
      React.Fragment,
      null,
      h(BeamBackground, { key: "beams" }),
      h(
        "div",
        { className: "hero-content container", key: "content" },
        h("div", { className: "hero-doc" }, h(TypingLine))
      )
    );
  }

  var root = document.getElementById("hero-root");
  if (root) {
    ReactDOM.createRoot(root).render(h(Hero));
  }
})();
