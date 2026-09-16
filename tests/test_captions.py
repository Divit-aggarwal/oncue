from itertools import pairwise

from video_automation.captions import segment, srt_time, to_srt
from video_automation.spec import Transcript, Word


def make(words, duration=10.0):
    return Transcript(
        engine="t",
        model="t",
        language="en",
        duration=duration,
        words=[Word(text=t, start=s, end=e) for t, s, e in words],
    )


def test_segments_respect_length_gaps_and_sentences():
    t = make(
        [
            ("Basically", 0.0, 0.4),
            ("RAG", 0.5, 0.8),
            ("mein", 0.9, 1.0),
            ("model", 1.1, 1.4),
            ("ko", 1.5, 1.6),
            ("dobara", 1.7, 2.0),
            ("train", 2.1, 2.4),
            ("nahi.", 2.5, 2.8),
            ("Hum", 2.9, 3.0),
            ("bas", 5.0, 5.2),
        ]
    )
    captions = segment(t, max_chars=20, max_gap=0.6)
    assert [c.text for c in captions] == [
        "Basically RAG mein",
        "model ko dobara",
        "train nahi.",
        "Hum",
        "bas",
    ]
    assert all(len(c.text) <= 20 for c in captions)
    assert all(a.end <= b.start for a, b in pairwise(captions))
    assert captions[-1].end <= t.duration
    assert sum(len(c.text.split()) for c in captions) == len(t.words)


def test_devanagari_and_hinglish_are_preserved_verbatim():
    t = make([("मॉडल", 0.0, 0.3), ("ko", 0.4, 0.5), ("दोबारा", 0.6, 0.9), ("train", 1.0, 1.2)])
    assert segment(t, 40, 0.6)[0].text == "मॉडल ko दोबारा train"


def test_srt_format():
    assert srt_time(3725.5) == "01:02:05,500"
    t = make([("hello", 0.0, 0.5)])
    assert to_srt(segment(t, 40, 0.6)) == "1\n00:00:00,000 --> 00:00:00,900\nhello\n\n"


def test_overlapping_whisper_timestamps_do_not_overlap_captions():
    t = make([("pehla.", 0.0, 1.5), ("doosra", 1.2, 1.6)])
    captions = segment(t, 40, 0.6)
    assert len(captions) == 2
    assert captions[0].end <= captions[1].start
    assert captions[0].end >= captions[0].start


def test_words_timestamped_past_the_audio_stay_inside_the_video():
    captions = segment(make([("a.", 0.0, 1.0), ("b", 2.05, 2.2)], duration=2.0), 40, 0.6)
    assert all(0 <= c.start <= c.end <= 2.0 for c in captions)
