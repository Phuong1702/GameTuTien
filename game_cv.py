import math

import pygame

from game_utils import clamp, norm

def detect_fingers(hand, handed_label):
    lm = hand.landmark
    count = 0
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        if lm[pip].y - lm[tip].y > 0.035:
            count += 1
    thumb_span = lm[4].x - lm[2].x
    thumb_open = thumb_span > 0.055 if handed_label == "Left" else thumb_span < -0.055
    if thumb_open:
        count += 1
    return min(5, count)


def detect_fist(hand):
    lm = hand.landmark
    closed = 0
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        if lm[tip].y > lm[pip].y - 0.015:
            closed += 1
    tips = [lm[i] for i in (8, 12, 16, 20)]
    palm = lm[9]
    palm_size = max(0.045, math.hypot(lm[5].x - lm[17].x, lm[5].y - lm[17].y))
    compact = sum(math.hypot(t.x - palm.x, t.y - palm.y) for t in tips) / 4.0
    return closed / 4.0 * 0.72 + clamp(1.0 - compact / (palm_size * 2.35), 0.0, 1.0) * 0.28


def is_index_pose(hand):
    lm = hand.landmark
    index_up = (lm[6].y - lm[8].y) > 0.035
    middle_up = (lm[10].y - lm[12].y) > 0.030
    ring_up = (lm[14].y - lm[16].y) > 0.030
    pinky_up = (lm[18].y - lm[20].y) > 0.030
    return index_up and not middle_up and not ring_up and not pinky_up


def detect_cv(hands_result, pose_result):
    control = {
        "move": pygame.Vector2(),
        "aim": pygame.Vector2(1, 0),
        "fingers": 0,
        "fist": 0.0,
        "clasp": 0.0,
        "left_seen": False,
        "right_seen": False,
        "right_pos": None,
        "index_pose": False,
    }
    labels = []
    left_wrist = None
    right_wrist = None
    if hands_result is not None and hands_result.multi_handedness:
        labels = [item.classification[0].label for item in hands_result.multi_handedness]

    if hands_result is not None and hands_result.multi_hand_landmarks:
        for hand_idx, hand in enumerate(hands_result.multi_hand_landmarks):
            label = labels[hand_idx] if hand_idx < len(labels) else "hand"
            landmarks = hand.landmark
            wrist = landmarks[0]
            tip = landmarks[8]
            wrist_vec = pygame.Vector2(wrist.x, wrist.y)
            hand_dir = pygame.Vector2(tip.x - wrist.x, tip.y - wrist.y)
            if label == "Left":
                control["left_seen"] = True
                left_wrist = wrist_vec
                control["move"] = norm(hand_dir) if hand_dir.length() > 0.03 else pygame.Vector2()
            else:
                control["right_seen"] = True
                right_wrist = wrist_vec
                control["right_pos"] = wrist_vec
                if hand_dir.length() > 0.03:
                    control["aim"] = norm(hand_dir)
                control["fingers"] = detect_fingers(hand, label)
                control["fist"] = max(control["fist"], detect_fist(hand))
                control["index_pose"] = is_index_pose(hand)

    if left_wrist is not None and right_wrist is not None:
        hands_dist = left_wrist.distance_to(right_wrist)
        if hands_dist > 0.001:
            control["clasp"] = max(control["clasp"], clamp(1.0 - hands_dist / 0.24, 0.0, 1.0))

    if pose_result is not None and pose_result.pose_landmarks is not None:
        lm = pose_result.pose_landmarks.landmark
        lw, rw = lm[15], lm[16]
        if min(lw.visibility, rw.visibility) > 0.35:
            dist = math.hypot(lw.x - rw.x, lw.y - rw.y)
            control["clasp"] = clamp(1.0 - dist / 0.20, 0.0, 1.0)
    return control


