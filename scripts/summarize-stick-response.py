#!/usr/bin/env python3
"""Aggregate measured SRT/MuJoCo trials and export a static response chart."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import statistics


def valid(trial):
    steady=trial.get('steady')
    return bool(steady and trial.get('completed') and trial.get('upright') and trial.get('mapping_ok')
                and steady['sim_seconds']>=5.5 and .95<=steady['realtime_factor']<=1.05
                and trial['loop_hz_min']>=45 and 'error' not in trial)


def aligned(trial):
    direction=trial['direction'];sign=-1 if direction in ['backward','right'] else 1
    return sign*trial['steady']['vx_m_s' if direction in ['forward','backward'] else 'yaw_deg_s']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline-aggregate',type=Path,
                        help='Overlay an earlier aggregate.json for the same stick settings')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    report=json.loads(args.source.read_text())
    if not report.get('complete'):parser.error('Measurement has not completed')
    groups=[]
    for direction in ['forward','backward','left','right']:
        for level in report['configuration']['levels']:
            trials=[t for t in report['trials'] if t['direction']==direction and t['stick_percent']==level]
            usable=[t for t in trials if valid(t)]
            values=[aligned(t) for t in usable]
            command=abs(trials[0]['command']['vx' if direction in ['forward','backward'] else 'vyaw'])
            if direction in ['left','right']:command=math.degrees(command)
            mean=statistics.mean(values) if values else None
            groups.append({'direction':direction,'stick_percent':level,'unit':'m/s' if direction in ['forward','backward'] else 'deg/s',
                           'command':command,'valid_trials':len(usable),'total_trials':len(trials),
                           'actual_mean':mean,'actual_std':statistics.stdev(values) if len(values)>1 else None,
                           'actual_min':min(values) if values else None,'actual_max':max(values) if values else None,
                           'actual_command_ratio':mean/command if mean is not None and command else None,
                           'values':values,'invalid_trials':[t['name'] for t in trials if not valid(t)]})
    summary={'source_complete':True,'groups':groups,
             'valid_trials':sum(valid(t) for t in report['trials']),'total_trials':len(report['trials']),
             'mapping_ok_trials':sum(t.get('mapping_ok',False) for t in report['trials']),
             'baseline':[t for t in report['trials'] if t['direction'] in ['neutral','deadzone']]}
    (args.output/'aggregate.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (args.output/'response.csv').open('w',newline='') as stream:
        fields=[k for k in groups[0] if k not in ['values','invalid_trials']]
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(groups)
    with (args.output/'trials.csv').open('w',newline='') as stream:
        fields=['name','repeat','direction','stick_percent','valid','completed','upright','mapping_ok','vx_m_s','yaw_deg_s','realtime_factor','min_trunk_m','max_tilt_deg','loop_hz_min']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for trial in report['trials']:
            row={k:trial.get(k) for k in fields};row['valid']=valid(trial)
            for k in ['vx_m_s','yaw_deg_s','realtime_factor']:row[k]=(trial.get('steady') or {}).get(k)
            writer.writerow(row)
    os.environ.setdefault('MPLCONFIGDIR',str(args.output/'.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    baseline = (json.loads(args.baseline_aggregate.read_text())['groups']
                if args.baseline_aggregate else [])
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained',sharey='row')
    for ax,direction in zip(axes.flat,['forward','backward','left','right']):
        data=[g for g in groups if g['direction']==direction]
        if baseline:
            before = [g for g in baseline if g['direction']==direction and g['actual_mean'] is not None]
            ax.errorbar([g['stick_percent'] for g in before], [g['actual_mean'] for g in before],
                        yerr=[g['actual_std'] or 0 for g in before], color='#777777', linestyle='--',
                        marker='s', capsize=4, label='Before: mean +/- SD')
        else:
            ax.plot([0,8]+[g['stick_percent'] for g in data],[0,0]+[g['command'] for g in data],color='#777777',linestyle='--',label='Requested command')
        available=[g for g in data if g['actual_mean'] is not None]
        if available:
            ax.errorbar([g['stick_percent'] for g in available],[g['actual_mean'] for g in available],
                        yerr=[g['actual_std'] or 0 for g in available],color='#087f8c',marker='o',capsize=4,
                        label='After: mean +/- SD' if baseline else 'Measured mean +/- SD')
            for g in available:
                ax.scatter([g['stick_percent']]*len(g['values']),g['values'],s=16,color='#087f8c',alpha=.45)
        for g in data:
            if g['valid_trials']!=g['total_trials']:
                ax.text(g['stick_percent'],.97,f"{g['valid_trials']}/{g['total_trials']} valid",transform=ax.get_xaxis_transform(),ha='center',va='top',fontsize=8,color='#b54828')
        ax.axvspan(0,8,color='#dddddd',alpha=.4);ax.axhline(0,color='#bbbbbb',linewidth=.7)
        ax.set(title=direction.capitalize(),xlabel='Raw joystick travel (%)',ylabel='Direction-aligned speed ('+data[0]['unit']+')',xticks=[0,8,25,50,75,100],xlim=(-3,103))
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    settings=report['configuration']
    fig.suptitle('Microduck V7RC: actual response vs joystick travel\n'
                 f"{settings['repeats']} fresh-scene trials per setting | "
                 f"steady window {settings['excluded_start_seconds']:g}-{settings['motion_seconds']:g} s",
                 fontsize=14)
    fig.savefig(args.output/'stick-response.png',dpi=170)
    fig.savefig(args.output/'stick-response.svg')
    plt.close(fig)
    print(json.dumps({k:summary[k] for k in ['valid_trials','total_trials','mapping_ok_trials']}))


if __name__=='__main__':main()
