import importlib
from math import pi

import numpy as np
from mathutils import Euler

from blender import objects
from bridge import abs_assignment
from utils import m_V, log

importlib.reload(abs_assignment)


class BridgePose(abs_assignment.DataAssignment):
    def __init__(self):
        self.references = {
            0: "cgt_nose",
            1: "cgt_left_eye_inner",
            2: "cgt_left_eye",
            3: "cgt_left_eye_outer",
            4: "cgt_right_eye_inner",
            5: "cgt_right_eye",
            6: "cgt_right_eye_outer",
            7: "cgt_left_ear",
            8: "cgt_right_ear",
            9: "cgt_mouth_left",
            10: "cgt_mouth_right",
            11: "cgt_left_shoulder",
            12: "cgt_right_shoulder",
            13: "cgt_left_elbow",
            14: "cgt_right_elbow",
            15: "cgt_left_wrist",
            16: "cgt_right_wrist",
            17: "cgt_left_pinky",
            18: "cgt_right_pinky",
            19: "cgt_left_index",
            20: "cgt_right_index",
            21: "cgt_left_thumb",
            22: "cgt_right_thumb",
            23: "cgt_left_hip",
            24: "cgt_right_hip",
            25: "cgt_left_knee",
            26: "cgt_right_knee",
            27: "cgt_left_ankle",
            28: "cgt_right_ankle",
            29: "cgt_left_heel",
            30: "cgt_right_heel",
            31: "cgt_left_foot_index",
            32: "cgt_right_foot_index"
        }

        self.arms = [
            [12, 17],  # right arm
            [11, 16]  # left arm_z
        ]

        self.legs = [
            [24, 26, 28, 30],  # right leg
            [23, 25, 27, 29]  # left leg
        ]

        self.shoulder_center = abs_assignment.CustomData()
        self.hip_center = abs_assignment.CustomData()

        self.pose = []
        self.col_name = "cgt_pose"
        self.rotation_data = []
        self.scale_data = []

    def init_references(self):
        # default empties
        self.pose = objects.add_empties(self.references, 0.025)
        objects.add_list_to_collection(self.col_name, self.pose, self.driver_col)

        self.init_bpy_driver_obj(
            self.shoulder_center, self.pose, 0.01, "shoulder_center", self.col_name, "SPHERE", [0, 0, 0])
        self.init_bpy_driver_obj(
            self.hip_center, self.pose, 0.01, "hip_center", self.col_name, "SPHERE", [0, 0, 0])

    def init_data(self):
        self.rotation_data = []
        self.scale_data = []
        self.average_rig_scale()
        # self.prepare_landmarks()
        # self.shoulder_hip_location()
        # self.shoulder_hip_rotation()
        # self.arm_angles()
        # self.test_arm_angles()
        # self.leg_angles()

    def average_rig_scale(self):
        avg_lengths = []
        for vertices in self.arms:
            # setup a joint [0, 0+2] for the arm vertices to get vector distances
            joints = [[self.data[vertex][1], self.data[vertex + 2][1]] for vertex in range(vertices[0], vertices[1] - 2, 2)]
            vertex_lengths = [m_V.get_vector_distance(joint[0], joint[1]) for joint in joints]

            # average lengths
            avg_length = sum(vertex_lengths) / len(vertex_lengths)
            avg_lengths.append(avg_length)

        avg_length = sum(avg_lengths) / len(avg_lengths)
        self.scale_data.append([15, [1, 1, avg_length]])
        self.scale_data.append([16, [1, 1, avg_length]])

    def update(self):
        # self.set_position()
        # self.set_rotation()
        self.set_scale()

    def set_position(self):
        """Keyframe the position of input data."""
        try:
            self.translate(self.pose, self.data, self.frame)

        except IndexError:
            log.logger.error("VALUE ERROR WHILE ASSIGNING POSE POSITION")

    def set_rotation(self):
        # self.euler_rotate(self.pose, self.rotation_data, self.frame)
        pass

    def set_scale(self):
        self.scale(self.pose, self.scale_data, self.frame)

    def arm_rot(self):
        origin = np.array([0, 0, 0])

        # approximate perpendicular points to origin
        forward_point = m_V.center_point(np.array(self.data[1][1]), np.array(self.data[4][1]))  # nose
        right_point = m_V.center_point(np.array(self.data[447][1]), np.array(self.data[366][1]))  # temple.R
        down_point = np.array(self.data[152][1])  # chin

        # direction vectors from imaginary origin
        normal = m_V.normalize(m_V.to_vector(origin, forward_point))
        tangent = m_V.normalize(m_V.to_vector(origin, right_point))
        binormal = m_V.normalize(m_V.to_vector(origin, down_point))

        # generate matrix to decompose it and access quaternion rotation
        matrix = m_V.generate_matrix(tangent, normal, binormal)
        loc, quart, scale = m_V.decompose_matrix(matrix)

    """ using blender internal method to track rotation. sadly bad results. """

    def arm_angles(self):
        # angle_offset = {
        #     'shoulder_r':   [.25, -.5, .7],
        #     'shoulder_l':   [-.25, .5, .7],
        #     'elbow_l':      [-.5,  .0, .5],
        #     'elbow_r':      [-.5,  .0, -.5]
        # }
        angle_offset = {
            'shoulder_r': [0, 0, 0],
            'shoulder_l': [.5, 0, 1.75],
            'elbow_l': [0, 0, 0],
            'elbow_r': [0, 0, 0],
        }

        # rotate shoulder to elbow and elbow to wrist
        shoulder_l = m_V.rotate_towards(self.data[11][1], self.data[13][1], track='Y', up='Z')
        shoulder_r = m_V.rotate_towards(self.data[12][1], self.data[14][1], track='X', up='Y')
        elbow_l = m_V.rotate_towards(self.data[13][1], self.data[15][1], track='-X', up='Z')
        elbow_r = m_V.rotate_towards(self.data[14][1], self.data[16][1], track='X', up='Z')

        # get euler combat with inverted offset
        shoulder_l = self.try_get_euler(shoulder_l, [e * -1 for e in angle_offset['shoulder_l']], 11)
        shoulder_r = self.try_get_euler(shoulder_r, [e * -1 for e in angle_offset['shoulder_r']], 12)
        elbow_l = self.try_get_euler(elbow_l, [e * -1 for e in angle_offset['elbow_l']], 13)
        elbow_r = self.try_get_euler(elbow_r, [e * -1 for e in angle_offset['elbow_r']], 14)

        # offset results
        shoulder_l = self.offset_euler(shoulder_l, angle_offset['shoulder_l'])
        elbow_l = self.offset_euler(elbow_l, angle_offset['elbow_l'])
        shoulder_r = self.offset_euler(shoulder_r, angle_offset['shoulder_r'])
        elbow_r = self.offset_euler(elbow_r, angle_offset['elbow_r'])

        data = [
            [11, shoulder_l],
            # [12, shoulder_r],
            # [13, elbow_l],
            # [14, elbow_r]
        ]
        # print(data, self.frame)
        for d in data:
            self.rotation_data.append(d)

    @staticmethod
    def offset_euler(euler, offset: []):
        rotation = Euler((
            euler[0] + pi * offset[0],
            euler[1] + pi * offset[1],
            euler[2] + pi * offset[2],
        ))
        return rotation

    def try_get_euler(self, quart_rotation, offset: [], prev_rot_idx: int):
        print("try get euler", offset, prev_rot_idx, self.frame)
        try:
            m_rot = m_V.to_euler(
                quart_rotation,
                Euler((
                    self.prev_rotation[prev_rot_idx][0] + pi * offset[0],
                    self.prev_rotation[prev_rot_idx][1] + pi * offset[1],
                    self.prev_rotation[prev_rot_idx][2] + pi * offset[2],
                ))
            )
        except KeyError:
            m_rot = m_V.to_euler(quart_rotation)
        print(m_rot)
        return m_rot

    def leg_angles(self):
        """ Get leg rotation data for driving the rig. """
        # get hip to knee rotation
        left_hip_x = m_V.null_axis([self.data[23][1], self.data[24][1]], 'Y')
        left_hip_z = m_V.null_axis([self.data[23][1], self.data[24][1]], 'Z')
        left_hip_x = m_V.angle_between(left_hip_x[0], left_hip_x[1])
        left_hip_z = m_V.angle_between(left_hip_z[0], left_hip_z[1])

        right_hip_x = m_V.null_axis([self.data[24][1], self.data[25][1]], 'Y')
        right_hip_z = m_V.null_axis([self.data[24][1], self.data[25][1]], 'Z')
        right_hip_x = m_V.angle_between(right_hip_x[0], right_hip_x[1])
        right_hip_z = m_V.angle_between(right_hip_z[0], right_hip_z[1])

        # get angles between knee and ankle
        left_knee_rot = m_V.angle_between(self.data[25][1], self.data[27][1])
        right_knee_rot = m_V.angle_between(self.data[26][1], self.data[28][1])

        data = [
            [23, Euler((left_hip_x - pi, 0, left_hip_z - pi))],
            [24, Euler((right_hip_x - pi * .75, 0, right_hip_z - pi))],
            [25, Euler((left_knee_rot, 0, 0))],
            [26, Euler((right_knee_rot, 0, 0))]
        ]

        for d in data:
            self.rotation_data.append(d)

    def shoulder_hip_rotation(self):
        """ Creates custom rotation data for driving the rig. """
        # rotate custom shoulder center point from shoulder.R to shoulder.L
        self.shoulder_center.rot = m_V.rotate_towards(self.data[11][1], self.data[12][1])
        # rotate custom hip center point from hip.R to hip.L
        self.hip_center.rot = m_V.rotate_towards(self.data[23][1], self.data[24][1])

        # todo: add combat euler
        self.hip_center.rot = m_V.to_euler(self.hip_center.rot)
        self.shoulder_center.rot = m_V.to_euler(self.shoulder_center.rot)

        # offset rotations
        r = self.shoulder_center.rot
        self.shoulder_center.rot = Euler((r[0], r[1], r[2]))
        self.shoulder_center.rot = Euler((r[0] - pi * .5, r[1], r[2] - pi * .5))

        r = self.hip_center.rot
        self.hip_center.rot = Euler((r[0], r[1], r[2]))
        self.hip_center.rot = Euler((r[0] - pi * .5, r[1], r[2] - pi * .5))

        # setup data format
        data = [
            [self.shoulder_center.idx, self.shoulder_center.rot],
            [self.hip_center.idx, self.hip_center.rot]
        ]

        for d in data:
            self.rotation_data.append(d)

    def shoulder_hip_location(self):
        """ Appending custom location data for driving the rig. """
        self.shoulder_center.loc = m_V.center_point(self.data[11][1], self.data[12][1])
        self.data.append([self.shoulder_center.idx, self.shoulder_center.loc])

        self.hip_center.loc = m_V.center_point(self.data[23][1], self.data[24][1])
        self.data.append([self.hip_center.idx, self.hip_center.loc])

    def prepare_landmarks(self):
        """ setting face mesh position to approximate origin """
        self.data = [[idx, np.array([-lmrk[0], lmrk[2], -lmrk[1]])] for idx, lmrk in self.data]

    def test_arm_angles(self):
        # get arms (shoulder / elbow / wrist) x-rot
        arms_x, arms_z = self.get_joint_segments(self.arms, [[1, 0, 1], [0, 1, 1]],
                                                 [self.data[11][1], self.data[12][1]])

        # joints for calculating angles
        joints = [[0, 1, 2], [1, 2, 3]]
        x_angles = m_V.joint_angles(arms_x, joints)
        z_angles = m_V.joint_angles(arms_z, joints)

        # setup formatting
        angle_data = self.old_format(
            x_angles, z_angles, self.arms,
            [#[11, [0, 0, -.0], [0, 0, 1]]
             #[12, [0, 0, 0], [1.5, 0, 0]]
             #[13, [0, 0, 0], [1, 1, 0]],
             #[14, [-.25, 0, 0]]
             ])

    def get_joint_segments(self, joints, axis=[[1, 1, 1], [1, 1, 1]], origin=[[0, 0, 0], [0, 0, 0]]):
        """ required input: tuple containing joint start and end, axis to track, origin.
         returns an array containing bones - axis can be nulled using the axis """
        joint_segments_x = []
        joint_segments_y = []

        def get_joint_segments(joint_range, joint_origin, axis):
            segments = [joint_origin]
            for idx in range(joint_range[0], joint_range[1], 2):
                joint_segment = np.array([self.data[idx][1][0] * axis[0],
                                          self.data[idx][1][1] * axis[1],
                                          self.data[idx][1][2] * axis[2]])
                segments.append(joint_segment)
            return segments

        for index, joint in enumerate(joints):
            segments = get_joint_segments(joint, np.array(
                [origin[index][0] * axis[index][0],
                 origin[index][1] * axis[index][1],
                 origin[index][2] * axis[index][2]]), axis[index])
            if index == 0:
                joint_segments_x = segments

            elif index == 1:
                joint_segments_y = segments

        return joint_segments_x, joint_segments_y

    def old_format(self, angle_data_x, angle_data_y, target, offset=[[0, [0, 0, 0], [1, 1, 1]]]):
        if angle_data_x is None or angle_data_y is None:
            return []

        # assign every angle data to the bone joint
        angle_data = [[angle_data_x[idx], angle_data_y[idx]] for idx, _ in enumerate(angle_data_x)]

        def apply_offset(joint_seg_idx):
            for angle_offset in offset:
                if joint_seg_idx == angle_offset[0]:
                    joint_angle = [joint_seg_idx, self.offset_euler(
                        [angles[0]*angle_offset[2][0],
                         0,
                         angles[1] * angle_offset[2][2]
                         ], angle_offset[1])]
                    self.rotation_data.append(joint_angle)

        def assign_angles_to_joints(joint_target):
            start, end = joint_target
            for joint_seg in range(start, end - 1, 2):
                apply_offset(joint_seg)

        # set the angle data
        for idx, angles in enumerate(angle_data):
            if angles[0] == None or angles[1] == None:
                break
            assign_angles_to_joints(target[idx])