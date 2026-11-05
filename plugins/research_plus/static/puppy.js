// Original vector mascot: elongated drop ears and a distinct canine muzzle.
const NS='http://www.w3.org/2000/svg';let serial=0;
const artwork=fetch('/static/dog.svg').then(r=>{if(!r.ok)throw Error('Puppy art unavailable');return r.text()});
export function createPuppy(host){
 let svg,enabled=true,mode='idle',timer,disposed=false;const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 host.classList.add('vectorPuppy');host.setAttribute('aria-label','奶油色垂耳小狗');
 function sync(){if(svg){svg.classList.toggle('puppy-animated',enabled&&!reduced.matches);svg.dataset.mode=mode}}
 artwork.then(text=>{if(disposed)return;svg=new DOMParser().parseFromString(text,'image/svg+xml').documentElement;const suffix='-paw-'+(++serial);svg.querySelectorAll('[id]').forEach(n=>{const old=n.id;n.id+=suffix;svg.querySelectorAll('[fill],[stroke]').forEach(e=>{for(const a of ['fill','stroke'])if(e.getAttribute(a)==='url(#'+old+')')e.setAttribute(a,'url(#'+old+suffix+')')})});const style=document.createElementNS(NS,'style');style.textContent=`
 .puppy-head{transform-origin:201px 232px}.puppy-tail{transform-origin:273px 282px}.puppy-eyes{transform-origin:201px 158px}
 .puppy-animated .puppy-head{animation:paw-breathe 5s ease-in-out infinite}.puppy-animated .puppy-eyes{animation:paw-blink 6s infinite}.puppy-animated .puppy-tail{animation:paw-wag 2.8s ease-in-out infinite}
 [data-action=think] .puppy-head{transform:rotate(-8deg);animation:none}.puppy-animated[data-action=nod] .puppy-head,.puppy-animated[data-action=explain] .puppy-head{animation:paw-nod .8s ease-in-out 3}
 [data-action=pet] .puppy-eyes,[data-mode=rest] .puppy-eyes{transform:scaleY(.15);animation:none}
 @keyframes paw-breathe{0%,100%{transform:rotate(-2deg) translateY(0)}50%{transform:rotate(1deg) translateY(-2px)}}
 @keyframes paw-blink{0%,43%,47%,100%{transform:scaleY(1)}45%{transform:scaleY(.08)}}
 @keyframes paw-wag{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(5deg)}}
 @keyframes paw-nod{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(4deg)}}
 @media(prefers-reduced-motion:reduce){*{animation:none!important}}
 `;svg.prepend(style);svg.style.cssText='position:absolute;inset:0;width:100%;height:100%;overflow:visible';host.append(svg);host.classList.add('vector-ready');sync()}).catch(()=>{});
 function act(name){clearTimeout(timer);host.dataset.action=name;if(svg)svg.dataset.action=name;timer=setTimeout(()=>{host.dataset.action='idle';if(svg)svg.dataset.action='idle'},2200)}
 reduced.addEventListener('change',sync);
 return {preferences(on){enabled=Boolean(on);sync()},pet(){act('pet')},act,setMode(value){mode=value;sync()},dispose(){disposed=true;clearTimeout(timer);reduced.removeEventListener('change',sync);svg?.remove();host.classList.remove('vector-ready')}};
}
