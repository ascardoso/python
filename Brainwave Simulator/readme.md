# Brainwave Sonification Simulator

Five sliders stand in for the strength of each EEG band. The page turns them into instruments and notes, so you can design the mapping before any electrodes exist. Everything here is simulated data, not a real brain signal.

## Scenario

Pressing a scenario glides the sliders to a typical pattern. Eyes closed raises alpha, which is the test I suggested for real hardware.

## Band power and instrument

## Signal and artifacts

[x] Reject artifacts [x] Natural drift

A blink briefly swamps the delta and theta bands. With rejection on, the page holds the last clean values, as a real product must.

## Sound

Volume

## Simulated raw trace

## MIDI out (for a real synth such as the SAM2695)

Needs a browser with Web MIDI (such as Chrome) and a MIDI device. The built-in sounds here approximate the General MIDI instruments chosen above.

## MIDI messages

```

```

## How the mapping works

Delta and theta are slow, so they drive sustained pads whose volume follows band power. Alpha, beta and gamma are faster, so each plays notes from the chosen scale. The stronger the band, the more often it plays. Values are smoothed, otherwise the music would jitter. Each band uses its own MIDI channel (1 to 5), with volume sent as CC11 and an instrument change at connection.