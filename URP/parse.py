import re
import json
from settings import course_timeDetail_combine


class Timetable:
    def __init__(self):
        self.course_time_dict = {
            '1': {'startTime': '08:00', 'endTime': '08:45'},
            '2': {'startTime': '08:50', 'endTime': '09:35'},
            '3': {'startTime': '10:05', 'endTime': '10:50'},
            '4': {'startTime': '10:55', 'endTime': '11:40'},
            '5': {'startTime': '13:30', 'endTime': '14:15'},
            '6': {'startTime': '14:20', 'endTime': '15:05'},
            '7': {'startTime': '15:35', 'endTime': '16:20'},
            '8': {'startTime': '16:25', 'endTime': '17:10'},
            '9': {'startTime': '18:00', 'endTime': '18:45'},
            '10': {'startTime': '18:50', 'endTime': '19:35'},
            '11': {'startTime': '19:40', 'endTime': '20:25'},
        }

    def get_time(self, session_index):
        return self.course_time_dict.get(
            str(session_index),
            {
                'startTime': '',
                'endTime': ''
            }
        )


class CourseDetail:
    def __init__(self, detail_data, timetable, course_timeDetail_combine):
        self.day = detail_data.get('classDay', '')
        self.building = detail_data.get('teachingBuildingName', '')
        self.classroom = detail_data.get('classroomName', '')
        self.sessionStart = detail_data.get('classSessions', '')
        self.sessionContinue = detail_data.get('continuingSession', '')
        self.timeDetail = []

        session_start = int(self.sessionStart or 0)
        session_continue = int(self.sessionContinue or 0)

        if session_start == 0 or session_continue == 0:
            # 如果 session_start 或 session_continue 为 0，不处理时间详情
            pass
        else:
            if course_timeDetail_combine == 0:
                # 合并节次，只显示课程的开始-结束时间
                time_start = timetable.get_time(session_start)['startTime']
                time_end = timetable.get_time(session_start + session_continue - 1)['endTime']
                self.timeDetail.append({
                    "startTime": time_start,
                    "endTime": time_end
                })
            else:
                # 分开节次，显示每个节次的开始时间和结束时间
                for i in range(session_start, session_start + session_continue):
                    time_info = timetable.get_time(i)
                    self.timeDetail.append({
                        "sessionIndex": i,
                        "startTime": time_info['startTime'],
                        "endTime": time_info['endTime']
                    })

    def to_dict(self):
        return {
            "day": self.day,
            "building": self.building,
            "classroom": self.classroom,
            "sessionStart": self.sessionStart,
            "sessionContinue": self.sessionContinue,
            "timeDetail": self.timeDetail
        }


class Course:
    def __init__(self, course_info, timetable, course_timeDetail_combine):
        self.Name = course_info.get('courseName', '')
        self.Code = course_info.get('id', {}).get('coureNumber', '')
        self.Property = course_info.get('coursePropertiesName', '')
        self.Teacher = course_info.get('attendClassTeacher', '').split('*')[0]
        self.Unit = course_info.get('unit', '')

        self.Detail = []

        time_and_place_list = course_info.get('timeAndPlaceList', [])

        if time_and_place_list:
            for time_place in time_and_place_list:
                detail = CourseDetail(time_place, timetable, course_timeDetail_combine)
                self.Detail.append(detail)

            # Get Week and courseNumber
            self.Week = time_and_place_list[0].get('weekDescription', '')

        else:
            # 当 timeAndPlaceList 为空时，不处理课程详情
            self.Week = ''

    def to_dict(self):
        return {
            "Name": self.Name,
            "Code": self.Code,
            "Property": self.Property,
            "Teacher": self.Teacher,
            "Unit": self.Unit,
            "Week": self.Week,
            "Detail": [detail.to_dict() for detail in self.Detail]
        }


class CourseList:
    def __init__(self, source, is_file=False):
        self.course_list = self.__parse__(source, is_file)

    def __parse__(self, source, is_file):
        if not source:
            raise ValueError('文本或文件路径不能为空！')

        if is_file:
            with open(source, 'r', encoding='UTF-8') as f:
                source = f.read()

        data = json.loads(source)

        if 'xkxx' not in data:
            raise ValueError('未找到选课信息！')

        timetable = Timetable()
        course_list = []

        for course_dict in data['xkxx']:
            for _, course_info in course_dict.items():
                course = Course(course_info, timetable, course_timeDetail_combine)
                course_list.append(course)

        return course_list

    def __iter__(self):
        return iter(self.course_list)

    def toString(self):
        return json.dumps([course.to_dict() for course in self.course_list], ensure_ascii=False, indent=4)


class CodeParser:
    def __init__(self):
        pass

    @staticmethod
    def urp_find_semester_plancode(source: str, is_file: bool = False) -> str:
        '''
        获取当前学期的课表地址
        传入参数为文件路径时，is_file参数必须为True

        Args:
            source: 响应文本或响应文件路径

        Returns:
            str: 当前学期的课表地址
        '''
        plan_code = ''

        if not source:
            raise ValueError('请求文本或文件路径不能为空！')

        if is_file:
            with open(source, 'r', encoding='UTF-8') as f:
                source = f.read()

        match = re.search(r'/student/courseSelect/thisSemesterCurriculum/(\w+)/ajaxStudentSchedule', source)
        if match:
            plan_code = match.group(1)
        else:
            raise ValueError('未找到课表地址！')

        return plan_code

    @staticmethod
    def urp_find_unpassexam_code(source: str, is_file: bool = False) -> str:
        '''
        获取未通过考试的课程地址
        传入参数为文件路径时, is_file参数必须为True

        Args:
            source: 响应文本或响应文件路径

        Returns:
            str: 未通过考试的课程地址
        '''
        code = ''

        if not source:
            raise ValueError('请求文本或文件路径不能为空！')

        if is_file:
            with open(source, 'r', encoding='UTF-8') as f:
                source = f.read()

        match = re.search(r'/student/integratedQuery/scoreQuery/(\w+)/unpassed/scores/callback', source)
        if match:
            code = match.group(1)
        else:
            raise ValueError('未找到未通过考试的课程地址！')

        return code
