import importlib

import m_CONST
from _blender.rig import abs_rigging
from _blender.rig.abs_rigging import DriverType, MappingRelation
from _blender.rig.utils import limb_drivers
from _blender.utils import objects
from utils import m_V

importlib.reload(m_CONST)
importlib.reload(m_V)
importlib.reload(objects)
importlib.reload(abs_rigging)
importlib.reload(limb_drivers)


class RigPose(abs_rigging.BpyRigging):
    pose_constraints = {
        # plain copy rotation
        m_CONST.POSE.hip_center.value: ["torso", "COPY_ROTATION"],
        m_CONST.POSE.shoulder_center.value: ["chest", "COPY_ROTATION"],

        # copy pose driver location
        m_CONST.POSE.left_hand_ik.value: ["hand_ik.R", "COPY_LOCATION"],
        m_CONST.POSE.right_hand_ik.value: ["hand_ik.L", "COPY_LOCATION"],
        m_CONST.POSE.left_forearm_ik.value: ["forearm_tweak.R", "COPY_LOCATION"],
        m_CONST.POSE.right_forearm_ik.value: ["forearm_tweak.L", "COPY_LOCATION"],

        # damped track to pose driver
        m_CONST.POSE.left_index_ik.value: ["hand_ik.R", "DAMPED_TRACK"],
        m_CONST.POSE.right_index_ik.value: ["hand_ik.L", "DAMPED_TRACK"]
    }

    driver_targets = [
        m_CONST.POSE.left_forearm_ik.value, m_CONST.POSE.left_hand_ik.value, m_CONST.POSE.left_index_ik.value,
        m_CONST.POSE.right_forearm_ik.value, m_CONST.POSE.right_hand_ik.value, m_CONST.POSE.right_index_ik.value
    ]

    rigify_joints = [
        ["upper_arm_fk.R", "forearm_fk.R"], ["forearm_fk.R", "hand_fk.R"], ["hand_fk.R", "f_middle.01_master.R"],
        ["upper_arm_fk.L", "forearm_fk.L"], ["forearm_fk.L", "hand_fk.L"], ["hand_fk.L", "f_middle.01_master.L"],
    ]

    ik_driver_origins = [
        m_CONST.POSE.left_shoulder.value, m_CONST.POSE.left_forearm_ik.value, m_CONST.POSE.left_hand_ik.value,
        m_CONST.POSE.right_shoulder.value, m_CONST.POSE.right_forearm_ik.value, m_CONST.POSE.right_hand_ik.value,
    ]

    detected_joints = [
        [m_CONST.POSE.left_shoulder.value, m_CONST.POSE.left_elbow.value],
        [m_CONST.POSE.left_elbow.value, m_CONST.POSE.left_wrist.value],
        [m_CONST.POSE.left_wrist.value, m_CONST.POSE.left_index.value],

        [m_CONST.POSE.right_shoulder.value, m_CONST.POSE.right_elbow.value],
        [m_CONST.POSE.right_elbow.value, m_CONST.POSE.right_wrist.value],
        [m_CONST.POSE.right_wrist.value, m_CONST.POSE.right_index.value]
    ]

    driver_offset_bones = [
        "upper_arm_fk.R", None, None,
        "upper_arm_fk.L", None, None
    ]

    mapping_relation_list = []

    def __init__(self, armature, driver_objects: list):
        self.pose_bones = armature.pose.bones
        self.limb_drivers = [limb_drivers.LimbDriver(
            driver_target=driver,
            driver_origin=self.ik_driver_origins[idx],
            detected_joint=self.detected_joints[idx],
            rigify_joint=self.rigify_joints[idx],
            pose_bones=self.pose_bones,
            offset_bone=self.driver_offset_bones[idx]
        ) for idx, driver in enumerate(self.driver_targets)]

        self.method_mapping = {
            DriverType.limb_driver: self.add_driver_batch,
            DriverType.constraint: self.add_constraint
        }

        # pose driver setup based on input rig
        for driver in self.limb_drivers:
            driver.set_expressions()

        self.set_relation_dict(driver_objects)
        self.apply_drivers()

    # region mapping
    def set_relation_dict(self, driver_objects: list):
        """ Sets a list of relations for further data transfer. """
        driver_names = [obj.name for obj in driver_objects]
        # pose driver objects
        self.add_pose_driver_mapping(driver_names, driver_objects)
        self.add_constraint_mapping(driver_names, driver_objects)

    def add_pose_driver_mapping(self, driver_names, driver_objects):
        def setup_relation(pose_driver):
            if pose_driver.name in driver_names:
                print(pose_driver.name)
                # access the driver object which has been set up previously
                driver_obj = self.get_driver_object(pose_driver.name, driver_names, driver_objects)
                driver_type = DriverType.limb_driver
                # add pose driver expressions to mapping list
                for expression in pose_driver.expressions:
                    print(expression)
                    relation = MappingRelation(driver_obj, driver_type, expression)
                    self.mapping_relation_list.append(relation)

        for drivers in self.limb_drivers:
            for driver in drivers.pose_drivers:
                setup_relation(driver)

    def add_constraint_mapping(self, driver_names, driver_objects):
        for name in self.pose_constraints:
            if name in driver_names:
                # add constraint to mapping list
                driver_obj = self.get_driver_object(name, driver_names, driver_objects)
                driver_type = DriverType.constraint
                relation = MappingRelation(driver_obj, driver_type, self.pose_constraints[name])
                self.mapping_relation_list.append(relation)

    @staticmethod
    def get_driver_object(driver_name, driver_names, driver_objects):
        idx = driver_names.index(driver_name)
        return driver_objects[idx]
    # endregion

    # region apply drivers
    def apply_drivers(self):
        # log.logger.debug("\n\n")
        pose_bone_names = [bone.name for bone in self.pose_bones]

        def apply_by_type(values):
            print("VALUES", values)
            if driver.driver_type == DriverType.limb_driver:
                print("\nlimb_driver")
                target = objects.get_object_by_name(values[0])
                add_driver_batch = self.method_mapping[driver.driver_type]
                print(target, driver.source, values[1], values[2], values[3], values[4])
                add_driver_batch(target, driver.source, values[1], values[2], values[3], values[4])

            elif driver.driver_type == DriverType.constraint:
                print("\nconstraint driver")
                if values[0] in pose_bone_names:
                    idx = pose_bone_names.index(values[0])
                    pose_bone = self.pose_bones[idx]

                    add_constraint = self.method_mapping[driver.driver_type]
                    add_constraint(pose_bone, driver.source, values[1])

        for driver in self.mapping_relation_list:
            apply_by_type(driver.values[0])
    # endregion
    # endregion