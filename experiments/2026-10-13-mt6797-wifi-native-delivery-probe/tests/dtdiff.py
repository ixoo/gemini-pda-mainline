"""Property-level diff of two DTBs; phandle lists resolved to node paths using provider #*-cells."""
import re, subprocess, sys
CELLS = {'clocks':'#clock-cells','assigned-clocks':'#clock-cells','assigned-clock-parents':'#clock-cells','resets':'#reset-cells',
         'power-domains':'#power-domain-cells','mediatek,conn-power-domain':'#power-domain-cells','interrupts-extended':'#interrupt-cells',
         'phys':'#phy-cells','iommus':'#iommu-cells','dmas':'#dma-cells','gpios':'#gpio-cells','mboxes':'#mbox-cells',
         'thermal-sensors':'#thermal-sensor-cells','io-channels':'#io-channel-cells','mediatek,gce-client-reg':3,
         'gpio-ranges':3,'nvmem-cells':0,'memory-region':0,'interrupt-parent':0,'mediatek,larbs':0,'mediatek,smi':0,
         'infracfg':0,'access-controllers':0,'mediatek,apmixedsys':0,'mediatek,auxadc':0,'mediatek,infracfg':0,'mediatek,pericfg':0,
         'mediatek,mmsys':0,'mediatek,scpsys':0,'syscon':0,'cpus':0,'cpu':0,'mediatek,i2c-bus':0,'mediatek,syscon-pll':1,
         'mediatek,pctl-regmap':0,'regulator-coupled-with':0,'cooling-device':2,'mediatek,larb-id':None}
def parse(dtb):
    dts = subprocess.run(['dtc','-q','-I','dtb','-O','dts',dtb],check=True,capture_output=True,text=True).stdout
    nodes, stack = {}, []
    for line in dts.splitlines():
        t = line.strip()
        if not t or t.startswith('/dts-v1/') or t.startswith('//'): continue
        if t.endswith('{'):
            name = t[:-1].strip()
            path = '/' if name == '/' else ('/' + name if stack[-1]=='/' else stack[-1] + '/' + name)
            stack.append(path); nodes[path] = {}
        elif t == '};': stack.pop()
        else:
            m = re.match(r'([^=;]+?)\s*(=\s*(.*))?;$', t)
            if m: nodes[stack[-1]][m.group(1)] = m.group(3) if m.group(2) else '<flag>'
    ph = {int(p[k].strip('<>'),16): path for path, p in nodes.items() for k in ('phandle','linux,phandle') if k in p}
    def ncells(path, prop):
        v = nodes[path].get(prop); return int(v.strip('<>'),16) if v else 0
    out = {}
    for path, props in nodes.items():
        q = {}
        for k, v in props.items():
            if k in ('phandle','linux,phandle'): continue
            spec = CELLS.get(k, 0 if (k.endswith('-supply') or k.endswith('-gpios') or k.startswith('pinctrl-') and k[8:].isdigit() or k.endswith('-parent')) else None)
            if k.endswith('-gpios'): spec = '#gpio-cells'
            if spec is not None and v.startswith('<'):
                cells = re.findall(r'0x[0-9a-f]+', v); outc = []; i = 0
                while i < len(cells):
                    n = int(cells[i],16)
                    if n in ph:
                        outc.append('@'+ph[n]); extra = ncells(ph[n], spec) if isinstance(spec,str) else spec
                        outc.extend(cells[i+1:i+1+extra]); i += 1 + extra
                    else:
                        outc.append(cells[i]); i += 1
                v = '<' + ' '.join(outc) + '>'
            q[k] = v
        out[path] = q
    return out
a, b = parse(sys.argv[1]), parse(sys.argv[2])
only_a = sorted(set(a)-set(b)); only_b = sorted(set(b)-set(a))
print(f'nodes only in A ({len(only_a)}):'); [print('  ', n) for n in only_a]
print(f'nodes only in B ({len(only_b)}):'); [print('  ', n) for n in only_b]
print('property differences in shared nodes:')
for path in sorted(set(a)&set(b)):
    pa, pb = a[path], b[path]
    for k in sorted(set(pa)|set(pb)):
        if pa.get(k) != pb.get(k):
            print(f'  {path} :: {k}: A={str(pa.get(k))[:90]} | B={str(pb.get(k))[:90]}')
if len(sys.argv) > 3:
    print('--- A-only node contents'); [print(n, a[n]) for n in only_a]
