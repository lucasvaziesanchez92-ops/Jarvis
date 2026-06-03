import json

with open(r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis\brain_vertices.json') as f:
    data = json.load(f)

verts = data['positions']
print(f'Vertices: {len(verts)//3}')

out = r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis\brain_v5.html'

with open(out, 'w') as f:
    f.write('''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS Neural Hologram v5</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;background:#000005;overflow:hidden;font-family:'SF Mono','Fira Code',monospace}
canvas{display:block;width:100%;height:100%}
#hud{position:fixed;top:24px;left:28px;pointer-events:none;z-index:10}
#hud .brand{color:#00f2ff;font-size:24px;font-weight:700;letter-spacing:10px;text-shadow:0 0 30px rgba(0,242,255,0.9)}
#hud .sub{color:rgba(0,242,255,0.45);font-size:9px;letter-spacing:4px;margin-top:4px}
#status{position:fixed;bottom:28px;left:28px;display:flex;align-items:center;gap:10px;pointer-events:none;z-index:10}
#status .dot{width:10px;height:10px;border-radius:50%;background:#00ff88;box-shadow:0 0 15px #00ff88;animation:pulse 2s infinite}
#status .text{color:#00ff88;font-size:10px;letter-spacing:3px;text-transform:uppercase}
#controls{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);display:flex;gap:12px;z-index:10}
.btn{background:rgba(0,242,255,0.08);border:1px solid rgba(0,242,255,0.4);color:#00f2ff;padding:8px 18px;font-family:inherit;font-size:10px;letter-spacing:2px;text-transform:uppercase;cursor:pointer;transition:all 0.3s}
.btn:hover{background:rgba(0,242,255,0.25);box-shadow:0 0 15px rgba(0,242,255,0.3)}
.btn.active{background:rgba(0,242,255,0.35);box-shadow:0 0 20px rgba(0,242,255,0.5)}
#debug{position:fixed;top:10px;right:10px;color:#0f0;font-size:10px;z-index:10;opacity:0.6;pointer-events:none}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.6;transform:scale(1.5)}}
</style>
</head>
<body>
<div id="hud"><div class="brand">JARVIS</div><div class="sub">NEURAL HOLOGRAM v5.0</div></div>
<div id="status"><div class="dot" id="dot"></div><span class="text" id="statustext">NEURAL LINK ACTIVE</span></div>
<div id="controls">
  <button class="btn active" onclick="window.setState('idle',this)">IDLE</button>
  <button class="btn" onclick="window.setState('thinking',this)">THINKING</button>
  <button class="btn" onclick="window.setState('speaking',this)">SPEAKING</button>
</div>
<div id="debug"></div>
<script src="three_local.js"></script>
<script>
(function(){
  var dbg=document.getElementById('debug');
  function log(msg){dbg.innerHTML+=msg+'<br>';console.log(msg);}
  if(typeof THREE==='undefined'){log('ERROR: Three.js no cargo');return;}

  var BRAIN_VERTICES = [''')

    chunk_size = 3000
    for i in range(0, len(verts), chunk_size):
        chunk = verts[i:i+chunk_size]
        f.write(','.join(f'{v:.6f}' for v in chunk))
        if i + chunk_size < len(verts):
            f.write(',')

    f.write('''];
  log("[1/6] Vertices embebidos: "+(BRAIN_VERTICES.length/3).toLocaleString());

  var scene=new THREE.Scene();
  scene.fog=new THREE.FogExp2(0x000005,0.025);
  var W=window.innerWidth,H=window.innerHeight;
  var camera=new THREE.PerspectiveCamera(45,W/H,0.1,100);
  camera.position.set(0,0.3,6.5);

  var renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setSize(W,H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  renderer.setClearColor(0x000005);
  document.body.appendChild(renderer.domElement);
  log("[2/6] Renderer: WebGL "+(renderer.capabilities.isWebGL2?"2":"1"));

  function makeTex(){
    var c=document.createElement("canvas");c.width=128;c.height=128;
    var ctx=c.getContext("2d");
    var g=ctx.createRadialGradient(64,64,0,64,64,64);
    g.addColorStop(0,"rgba(255,255,255,1)");g.addColorStop(0.3,"rgba(255,255,255,0.85)");
    g.addColorStop(0.7,"rgba(255,255,255,0.2)");g.addColorStop(1,"rgba(255,255,255,0)");
    ctx.fillStyle=g;ctx.fillRect(0,0,128,128);
    var t=new THREE.CanvasTexture(c);t.minFilter=t.magFilter=THREE.LinearFilter;return t;
  }
  var TEX=makeTex();

  var brainGroup=new THREE.Group();
  brainGroup.position.y=0.2;
  scene.add(brainGroup);

  // WIREFRAME NEURAL
  var linkPositions=[];
  var maxDist=0.32;
  var stride=4;
  for(var i=0;i<BRAIN_VERTICES.length;i+=stride*3){
    var ax=BRAIN_VERTICES[i],ay=BRAIN_VERTICES[i+1],az=BRAIN_VERTICES[i+2];
    for(var j=i+stride*3;j<BRAIN_VERTICES.length;j+=stride*3){
      var dx=ax-BRAIN_VERTICES[j],dy=ay-BRAIN_VERTICES[j+1],dz=az-BRAIN_VERTICES[j+2];
      if(dx*dx+dy*dy+dz*dz<maxDist*maxDist&&Math.random()>0.75){
        linkPositions.push(ax,ay,az,BRAIN_VERTICES[j],BRAIN_VERTICES[j+1],BRAIN_VERTICES[j+2]);
      }
    }
  }
  var linkGeo=new THREE.BufferGeometry();
  linkGeo.setAttribute("position",new THREE.Float32BufferAttribute(linkPositions,3));
  var linkMat=new THREE.LineBasicMaterial({color:0x00aaff,transparent:true,opacity:0.22,blending:THREE.AdditiveBlending,depthWrite:false});
  var links=new THREE.LineSegments(linkGeo,linkMat);
  brainGroup.add(links);
  log("[3/6] Neural links: "+(linkPositions.length/6).toLocaleString());

  // PARTICULAS SUPERFICIE
  var surfGeo=new THREE.BufferGeometry();
  surfGeo.setAttribute("position",new THREE.Float32BufferAttribute(BRAIN_VERTICES,3));
  var surfMat=new THREE.PointsMaterial({size:0.06,map:TEX,alphaTest:0.04,transparent:true,opacity:0.85,blending:THREE.AdditiveBlending,depthWrite:false,color:new THREE.Color(0x00ffff)});
  var surfPoints=new THREE.Points(surfGeo,surfMat);
  brainGroup.add(surfPoints);

  // HALO DIFUSO
  var haloGeo=new THREE.IcosahedronGeometry(1.35,3);
  var haloMat=new THREE.MeshBasicMaterial({color:0x0033aa,transparent:true,opacity:0.04,depthWrite:false,side:THREE.BackSide});
  var halo=new THREE.Mesh(haloGeo,haloMat);
  brainGroup.add(halo);

  // ORBITALES
  var ORB=1200;
  var orbPos=new Float32Array(ORB*3);
  for(var i=0;i<ORB;i++){
    var a=Math.random()*Math.PI*2;
    var ly=Math.floor(Math.random()*8);
    var rx=2.8+ly*0.9+(Math.random()-0.5)*0.6;
    var y=(Math.random()-0.5)*4.0;
    orbPos[i*3]=Math.cos(a)*rx;
    orbPos[i*3+1]=y;
    orbPos[i*3+2]=Math.sin(a)*rx*(0.65+Math.random()*0.5);
  }
  var orbGeo=new THREE.BufferGeometry();
  orbGeo.setAttribute("position",new THREE.BufferAttribute(orbPos,3));
  var orbMat=new THREE.PointsMaterial({size:0.04,map:TEX,alphaTest:0.04,transparent:true,opacity:0.28,blending:THREE.AdditiveBlending,depthWrite:false,color:new THREE.Color(0x0088ff)});
  var orbPoints=new THREE.Points(orbGeo,orbMat);
  brainGroup.add(orbPoints);

  // ESTRELLAS FONDO
  var STAR=500;
  var starPos=new Float32Array(STAR*3);
  for(var i=0;i<STAR;i++){
    starPos[i*3]=(Math.random()-0.5)*25;
    starPos[i*3+1]=(Math.random()-0.5)*20;
    starPos[i*3+2]=(Math.random()-0.5)*15-5;
  }
  var starGeo=new THREE.BufferGeometry();
  starGeo.setAttribute("position",new THREE.BufferAttribute(starPos,3));
  var starMat=new THREE.PointsMaterial({size:0.02,map:TEX,alphaTest:0.04,transparent:true,opacity:0.12,blending:THREE.AdditiveBlending,depthWrite:false,color:new THREE.Color(0x0022aa)});
  var stars=new THREE.Points(starGeo,starMat);
  scene.add(stars);

  log("[4/6] Scene complete");

  var currentState="idle";
  var targetColor=new THREE.Color(0x00ffff);
  var secColor=new THREE.Color(0x0088ff);
  var colors={
    idle:{main:0x00ffff,sec:0x0088ff,dot:"#00ff88",glow:"0 0 15px #00ff88"},
    thinking:{main:0xffaa00,sec:0xff4400,dot:"#ffaa00",glow:"0 0 20px #ffaa00"},
    speaking:{main:0x00ff88,sec:0x00ffcc,dot:"#00ffcc",glow:"0 0 20px #00ffcc"}
  };
  window.setState=function(st,btn){
    currentState=st;
    var c=colors[st];
    targetColor.setHex(c.main);
    secColor.setHex(c.sec);
    var dot=document.getElementById("dot"),txt=document.getElementById("statustext");
    dot.style.background=c.dot;dot.style.boxShadow=c.glow;
    txt.textContent=st==="idle"?"NEURAL LINK ACTIVE":st==="thinking"?"PROCESSING NEURAL PATTERNS":"TRANSMITTING INTELLIGENCE";
    txt.style.color=c.dot;
    document.querySelectorAll(".btn").forEach(function(b){b.classList.remove("active");});
    if(btn)btn.classList.add("active");
  };

  var t=0;
  function animate(){
    requestAnimationFrame(animate);t+=0.016;
    var rs=currentState==="idle"?0.0015:currentState==="thinking"?0.009:0.004;
    brainGroup.rotation.y+=rs;
    orbPoints.rotation.y-=rs*0.2;
    halo.rotation.y+=rs*0.1;
    stars.rotation.y+=rs*0.05;
    surfMat.size=0.06+Math.sin(t*2.5)*0.008;
    orbMat.size=0.04+Math.sin(t*1.6)*0.006;
    linkMat.opacity=0.20+Math.sin(t*1.2)*0.08;
    surfMat.color.lerp(targetColor,0.04);
    orbMat.color.lerp(secColor,0.035);
    linkMat.color.lerp(targetColor,0.03);
    haloMat.color.lerp(targetColor,0.025);
    renderer.render(scene,camera);
  }
  animate();
  log("[5/6] Animation running");
  window.addEventListener("resize",function(){
    camera.aspect=window.innerWidth/window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth,window.innerHeight);
  });
  log("[6/6] BRAIN HOLOGRAM LIVE");
})();
</script>
</body>
</html>''')

print(f'Wrote brain_v5.html')
