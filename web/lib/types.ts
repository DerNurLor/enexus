// ── Lesson ────────────────────────────────────────────────────────────────────
export interface Lesson {
  subject:      string
  lesson_type:  string | null
  time_start:   string
  time_end:     string
  teacher_name: string | null
  teacher_id:   number | null
  classroom:    string | null   // field name in group schedule
  room_name:    string | null   // field name in teacher/room schedule
  subgroup:     string | null
  week_type:    string | null
  note:         string | null
}

// ── Day ───────────────────────────────────────────────────────────────────────
export interface DaySchedule {
  weekday_name: string
  week_number:  number
  lessons:      Lesson[]
}

// ── Group ─────────────────────────────────────────────────────────────────────
export interface GroupMeta {
  group_id:        number
  name:            string
  institute_name:  string
  speciality_name: string
  course:          number
  academic_year:   string
  has_schedule:    boolean
  days_count:      number
}

export interface GroupSchedule {
  group_id:            number
  name:                string
  speciality_name:     string
  course:              number
  academic_year:       string
  schedule_scraped_at: string | null
  refreshing:          string | null
  schedule:            Record<string, DaySchedule>
}

export interface DayResponse {
  group_id:   number
  name:       string
  date:       string
  refreshing: string | null
  lessons:    Lesson[]
  message:    string | null
}

// ── Search ────────────────────────────────────────────────────────────────────
export interface SearchResults {
  query: string
  results: {
    groups:   GroupMeta[]
    teachers: TeacherMeta[]
    rooms:    RoomMeta[]
  }
  counts: { groups: number; teachers: number; rooms: number }
}

export interface TeacherMeta {
  teacher_id:      number
  full_name:       string
  short_name:      string
  institute_names: string[]
  subjects:        string[]
}

export interface RoomMeta {
  room_id:  number
  name:     string
  building: string | null
  subjects: string[]
}
