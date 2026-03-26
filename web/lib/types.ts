export interface User {
  id: string
  handle: string
  role: 'student' | 'teacher' | 'parent'
  status: string
  detail_permission?: boolean
}

export interface SessionData {
  id: string
  handle: string
  role: 'student' | 'teacher' | 'parent'
  status: string
}

export interface ChatMessage {
  id: string
  student_user_id: string
  role: 'user' | 'assistant'
  content: string
  meta?: {
    subject?: string
    concept?: string
  }
  created_at: string
}

export interface ProblemSubmission {
  id: string
  student_user_id: string
  file_hash: string
  created_at: string
}

export interface ProblemItem {
  id: string
  student_user_id: string
  submission_id: string
  item_no: number
  is_correct: boolean
  key_concepts: string[]
  explanation_summary: string
  reason_category: string
  created_at: string
}

export interface ProblemItemFeedback {
  id: string
  student_user_id: string
  problem_item_id: string
  understanding: 'confused' | 'understood'
  reason_category: string
  created_at: string
}

export interface HomeworkAssignment {
  id: string
  student_user_id: string
  title: string
  description: string
  created_at: string
}

export interface HomeworkSubmission {
  id: string
  assignment_id: string
  student_user_id: string
  storage_path: string
  created_at: string
}

export interface HomeworkNonSubmitReason {
  id: string
  student_user_id: string
  assignment_id: string
  reason_code: 'forgot' | 'time' | 'hard'
  created_at: string
}

export interface TeacherStudentNote {
  teacher_user_id: string
  student_user_id: string
  note: string
  updated_at: string
}

export interface FocusEvent {
  id: string
  student_user_id: string
  event_type: 'left_tab' | 'returned_tab' | 'tab_closed'
  created_at: string
}

export interface StudentSummary {
  student: User
  recentSubmissions: ProblemSubmission[]
  weakConcepts: string[]
  homeworkRate: number
  chatCount: number
  correctRate: number
}

export interface GradedItem {
  item_no: number
  is_correct: boolean
  key_concepts: string[]
  explanation_summary: string
  reason_category: string
}
