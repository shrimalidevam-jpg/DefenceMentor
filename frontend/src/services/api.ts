const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface HealthResponse { status: string; service: string }
export interface User { id: string; email: string; full_name: string; role: 'student' | 'admin'; is_active: boolean }
export interface Profile { id: string; user_id: string; exam_target: string; current_level: string | null; target_exam_date: string | null; learning_preferences: string | null; academic_stream: 'Science' | 'Commerce' | 'Arts' | null; science_group: 'A' | 'B' | null; student_phone: string | null; parent_phone: string | null; guardian_report_consent_at: string | null }
export interface RegisterPayload { full_name: string; email: string; password: string; exam_target: string; current_level?: string; academic_stream: 'Science' | 'Commerce' | 'Arts'; science_group?: 'A' | 'B'; student_phone?: string; parent_phone: string; student_photo_data: string; parent_photo_data: string; guardian_report_consent: true }
export interface GoogleLoginPayload { credential: string }
export interface ProfileUpdate { exam_target?: string; current_level?: string | null; target_exam_date?: string | null; learning_preferences?: string | null; academic_stream?: 'Science' | 'Commerce' | 'Arts' | null; science_group?: 'A' | 'B' | null; student_phone?: string | null; guardian_report_consent?: boolean }
export interface Exam { id: string; name: string; code: string; description: string | null; display_order: number; is_active: boolean }
export interface Subject { id: string; exam_id: string; name: string; code: string; description: string | null; display_order: number }
export interface Chapter { id: string; subject_id: string; name: string; description: string | null; display_order: number }
export interface Topic { id: string; chapter_id: string; name: string; description: string | null; display_order: number }
export interface Concept { id: string; topic_id: string; name: string; description: string | null; display_order: number }
export interface Prerequisite { id: string; concept_id: string; prerequisite_concept_id: string; is_required: boolean }
export interface LearningPathItem { order: number; concept: Concept; is_target: boolean }
export interface ChatSession { id: string; title: string; subject_id: string | null; topic_id: string | null; learning_state: string | null; current_concept_id: string | null; created_at: string; updated_at: string }
export interface ChatDocumentSource { source_id: string; document_id: string; title: string; url: string; page_reference: string | null; relevance_score: number }
export interface ChatAttachment { id: string; file_name: string; media_type: string; size: number }
export interface ChatAttachmentUpload { file_name: string; media_type: string; data_base64: string }
export interface ChatMessage { id: string; chat_session_id: string; role: string; content: string; sources: ChatDocumentSource[]; attachments: ChatAttachment[]; created_at: string; updated_at: string }
export interface ChatDetail extends ChatSession { messages: ChatMessage[] }
export interface ChatCompletion { user_message: ChatMessage; assistant_message: ChatMessage; chat_title: string; provider: string; sources: ChatDocumentSource[] }
export interface DiagnosticOption { id: string; text: string; display_order: number }
export interface DiagnosticQuestion { id: string; concept_id: string | null; prompt: string; explanation: string | null; difficulty: string; question_type: string; options: DiagnosticOption[] }
export interface DiagnosticStart { target_concept_id: string; question_count: number; questions: DiagnosticQuestion[] }
export interface DiagnosticAnswer { question_id: string; concept_id: string | null; is_correct: boolean; mastery_score: number | null; explanation: string | null; next_step: string }
export interface LearningPathProgress { concept_id: string; name: string; description: string | null; is_target: boolean; mastery_score: number; status: string; completion_percent: number }
export interface LearningSession { id: string; target_concept_id: string; current_concept_id: string | null; status: string; objective: string | null; path: LearningPathProgress[] }
export interface Lesson { concept_id: string; title: string; definition: string; example: string; practice_guidance: string; mastery_score: number }
export interface PracticeQuestion { id: string; concept_id: string | null; prompt: string; difficulty: string; question_type: string; options: DiagnosticOption[] }
export interface LearningAnswer { question_id: string; concept_id: string | null; activity_type: string; is_correct: boolean; mastery_score: number | null; completion_percent: number; concept_status: string; next_concept_id: string | null; explanation: string | null }
export interface AssessmentQuestion { id: string; prompt: string; difficulty: string; question_type: string; round_name: string; question_number: number; total_questions: number; is_ai_generated: boolean; selected_option_id: string | null; options: DiagnosticOption[] }
export interface AssessmentAttempt { id: string; status: string; current_round: string; answered_count: number; schedule_type: 'weekly' | 'monthly'; section_time_limit_seconds: number; section_elapsed_seconds: number; section_completed: boolean; same_day_deadline: string | null; total_exam_questions: number; score: number | null; question: AssessmentQuestion | null }
export interface AssessmentMetric { correct_answers: number; total_questions: number; accuracy: number }
export interface AssessmentReport { attempt_id: string; status: string; score: number; total_questions: number; correct_answers: number; accuracy: number; round_performance: Record<string, number>; difficulty_performance: Record<string, AssessmentMetric>; subject_performance: Record<string, AssessmentMetric>; topic_performance: Record<string, AssessmentMetric>; average_response_time_seconds: number; net_marks: number; maximum_marks: number; recommendations: string[] }
export interface AssessmentHistoryItem { id: string; schedule_type: 'weekly' | 'monthly'; status: string; score: number | null; answered_count: number; started_at: string; completed_at: string | null }
export interface AssessmentHistory { exam_id: string; total_attempts: number; completed_attempts: number; average_score: number | null; previous_average_score: number | null; improvement_points: number | null; weekly_due: boolean; monthly_due: boolean; history: AssessmentHistoryItem[]; recommendations: string[] }
export interface VocabularyQuestion { id: string; word: string; options: Record<string, string>; explanation: string | null; example: string | null; selected_option: string | null; correct_option: string | null; is_correct: boolean | null }
export interface DailyGrowth { practice_date: string; questions: VocabularyQuestion[]; answered_count: number; correct_count: number; score_percent: number | null; ssb_tip: string; ssb_category: string; ssb_title: string }
export interface VocabularyAnswer { word_id: string; is_correct: boolean; correct_option: string; meaning: string; example: string; answered_count: number; correct_count: number; score_percent: number; answered_at: string }
export interface DailySSBGuidance { guidance_date: string; title: string; guidance: string; action: string; reflection_question: string }
export interface SSBGuidanceMessage { id: string; role: 'user' | 'assistant'; content: string; created_at: string }
export interface StudyPlanTask { id: string; plan_date: string; concept_id: string; concept_name: string; subject_name: string; task_type: 'learn' | 'revise' | 'practice'; estimated_minutes: number; display_order: number; mastery_score: number | null; is_completed: boolean; completed_at: string | null }
export interface StudyPlannerPreferences { planner_setup_complete: boolean; daily_study_minutes: number; study_start_time: string; focus_session_minutes: number; break_minutes: number; study_subjects: ('MATH' | 'GAT')[]; math_share_percent: number }
export interface StudyScheduleBlock { kind: 'focus' | 'break' | 'meal'; label: string; start_time: string; end_time: string; duration_minutes: number; task_id: string | null; concept_name: string | null; subject_name: string | null; is_completed: boolean }
export interface StudyPlan { plan_date: string; exam_target: string; target_exam_date: string | null; days_to_exam: number | null; total_minutes: number; completed_count: number; tasks: StudyPlanTask[]; schedule: StudyScheduleBlock[] }
export interface StudyCalendarTask { id: string; concept_name: string; subject_name: string; task_type: string; estimated_minutes: number; is_completed: boolean; completed_at: string | null }
export interface StudyCalendarExam { id: string; attempt_no: number; status: string; question_count: number; answered_count: number; correct_answers: number; score_marks: number; max_marks: number; score_percent: number | null; completed_at: string | null }
export interface StudyCalendarDay { plan_date: string; total_minutes: number; completed_minutes: number; completed_count: number; tasks: StudyCalendarTask[]; exams: StudyCalendarExam[] }
export interface StudyCalendar { month: string; days: StudyCalendarDay[] }
export interface DailyReviewQuestion { id: string; prompt: string; difficulty: string; question_number: number; total_questions: number; options: DiagnosticOption[] }
export interface DailyReview { id: string; plan_date: string; attempt_no: number; status: string; answered_count: number; question_count: number; correct_answers: number; score: number | null; score_marks: number; max_marks: number; question: DailyReviewQuestion | null }
export interface DailyReviewAnswer { is_correct: boolean | null; explanation: string | null; answered_count: number; correct_answers: number; completed: boolean; score: number | null; score_marks: number; max_marks: number; next_question: DailyReviewQuestion | null }

export class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiError(typeof payload?.detail === 'string' ? payload.detail : 'Request failed. Please try again.', response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  register: (payload: RegisterPayload) => request<User>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (email: string, password: string) => request<{ access_token: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  googleLogin: (credential: string) => request<{ access_token: string }>('/api/auth/google', { method: 'POST', body: JSON.stringify({ credential }) }),
  me: (token: string) => request<User>('/api/auth/me', {}, token),
  deleteAccount: (token: string) => request<void>('/api/auth/me', { method: 'DELETE' }, token),
  profile: (token: string) => request<Profile>('/api/auth/me/profile', {}, token),
  updateProfile: (token: string, data: ProfileUpdate) => request<Profile>('/api/auth/me/profile', { method: 'PATCH', body: JSON.stringify(data) }, token),
  exams: () => request<Exam[]>('/api/curriculum/exams'),
  subjects: (examId: string) => request<Subject[]>(`/api/curriculum/exams/${examId}/subjects`),
  chapters: (subjectId: string) => request<Chapter[]>(`/api/curriculum/subjects/${subjectId}/chapters`),
  topics: (chapterId: string) => request<Topic[]>(`/api/curriculum/chapters/${chapterId}/topics`),
  concepts: (topicId: string) => request<Concept[]>(`/api/curriculum/topics/${topicId}/concepts`),
  prerequisites: (conceptId: string) => request<Prerequisite[]>(`/api/curriculum/concepts/${conceptId}/prerequisites`),
  learningPath: (conceptId: string) => request<LearningPathItem[]>(`/api/curriculum/concepts/${conceptId}/learning-path`),
  chats: (token: string) => request<ChatSession[]>('/api/chats', {}, token),
  createChat: (token: string, title = 'New chat') => request<ChatSession>('/api/chats', { method: 'POST', body: JSON.stringify({ title }) }, token),
  draftChat: (token: string) => request<ChatSession>('/api/chats/draft', { method: 'POST' }, token),
  chat: (token: string, chatId: string) => request<ChatDetail>(`/api/chats/${chatId}`, {}, token),
  renameChat: (token: string, chatId: string, title: string) => request<ChatSession>(`/api/chats/${chatId}`, { method: 'PATCH', body: JSON.stringify({ title }) }, token),
  deleteChat: (token: string, chatId: string) => request<void>(`/api/chats/${chatId}`, { method: 'DELETE' }, token),
  sendMessage: (token: string, chatId: string, content: string) => request<ChatMessage>(`/api/chats/${chatId}/messages`, { method: 'POST', body: JSON.stringify({ content }) }, token),
  completeMessage: (token: string, chatId: string, content: string, oralExplanation = false, attachments: ChatAttachmentUpload[] = []) => request<ChatCompletion>(`/api/chats/${chatId}/messages/complete`, { method: 'POST', body: JSON.stringify({ content, oral_explanation: oralExplanation, attachments }) }, token),
  chatAttachment: async (token: string, chatId: string, messageId: string, attachmentId: string) => {
    const response = await fetch(`${API_BASE}/api/chats/${chatId}/messages/${messageId}/attachments/${attachmentId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new ApiError('Unable to download this chat attachment.', response.status)
    return response.blob()
  },
  startDiagnostic: (token: string, conceptId: string) => request<DiagnosticStart>(`/api/diagnostics/concepts/${conceptId}/start`, { method: 'POST' }, token),
  answerDiagnostic: (token: string, questionId: string, selectedOptionId: string) => request<DiagnosticAnswer>(`/api/diagnostics/questions/${questionId}/answer`, { method: 'POST', body: JSON.stringify({ selected_option_id: selectedOptionId }) }, token),
  createLearningSession: (token: string, conceptId: string) => request<LearningSession>('/api/learning/sessions', { method: 'POST', body: JSON.stringify({ target_concept_id: conceptId }) }, token),
  learningSession: (token: string, sessionId: string) => request<LearningSession>(`/api/learning/sessions/${sessionId}`, {}, token),
  lesson: (token: string, sessionId: string) => request<Lesson>(`/api/learning/sessions/${sessionId}/current/lesson`, {}, token),
  practiceQuestion: (token: string, sessionId: string) => request<PracticeQuestion>(`/api/learning/sessions/${sessionId}/current/practice`, {}, token),
    answerLearningQuestion: (token: string, sessionId: string, questionId: string, selectedOptionId: string, confidence: number) => request<LearningAnswer>(`/api/learning/sessions/${sessionId}/questions/${questionId}/answer`, { method: 'POST', body: JSON.stringify({ selected_option_id: selectedOptionId, confidence, activity_type: 'understanding_check' }) }, token),
    startAssessment: (token: string, examId: string, scheduleType: 'weekly' | 'monthly' = 'weekly') => request<AssessmentAttempt>('/api/assessments/start', { method: 'POST', body: JSON.stringify({ exam_id: examId, schedule_type: scheduleType }) }, token),
    assessment: (token: string, attemptId: string) => request<AssessmentAttempt>(`/api/assessments/${attemptId}`, {}, token),
    assessmentHistory: (token: string, examId: string) => request<AssessmentHistory>(`/api/assessments/history?exam_id=${encodeURIComponent(examId)}`, {}, token),
    navigateAssessment: (token: string, attemptId: string, questionId: string, selectedOptionId: string | null, targetQuestionNumber: number) => request<AssessmentAttempt>(`/api/assessments/${attemptId}/navigate`, { method: 'POST', body: JSON.stringify({ current_question_id: questionId, selected_option_id: selectedOptionId, target_question_number: targetQuestionNumber }) }, token),
    finishAssessmentSection: (token: string, attemptId: string, questionId: string, selectedOptionId: string | null) => request<AssessmentAttempt>(`/api/assessments/${attemptId}/finish-section`, { method: 'POST', body: JSON.stringify({ current_question_id: questionId, selected_option_id: selectedOptionId }) }, token),
    startGatSection: (token: string, attemptId: string) => request<AssessmentAttempt>(`/api/assessments/${attemptId}/start-gat`, { method: 'POST' }, token),
    submitAssessment: (token: string, attemptId: string, questionId: string, selectedOptionId: string | null) => request<AssessmentAttempt>(`/api/assessments/${attemptId}/submit`, { method: 'POST', body: JSON.stringify({ current_question_id: questionId, selected_option_id: selectedOptionId }) }, token),
    abandonAssessment: (token: string, attemptId: string) => request<AssessmentAttempt>(`/api/assessments/${attemptId}/abandon`, { method: 'POST' }, token),
    assessmentReport: (token: string, attemptId: string) => request<AssessmentReport>(`/api/assessments/${attemptId}/report`, {}, token),
    todayStudyPlan: (token: string) => request<StudyPlan>('/api/study-planner/today', {}, token),
    studyCalendar: (token: string, month: string) => request<StudyCalendar>(`/api/study-planner/calendar?month=${encodeURIComponent(month)}`, {}, token),
    studyPlannerPreferences: (token: string) => request<StudyPlannerPreferences>('/api/study-planner/preferences', {}, token),
    updateStudyPlannerPreferences: (token: string, preferences: StudyPlannerPreferences) => request<StudyPlannerPreferences>('/api/study-planner/preferences', { method: 'PUT', body: JSON.stringify(preferences) }, token),
    tomorrowStudyPlan: (token: string) => request<StudyPlan>('/api/study-planner/tomorrow', {}, token),
    regenerateTomorrowStudyPlan: (token: string) => request<StudyPlan>('/api/study-planner/tomorrow/regenerate', { method: 'POST' }, token),
    updateStudyTask: (token: string, taskId: string, isCompleted: boolean) => request<StudyPlan>(`/api/study-planner/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify({ is_completed: isCompleted }) }, token),
    startDailyReview: (token: string) => request<DailyReview>('/api/daily-review/today/start', { method: 'POST' }, token),
    startStudyReview: (token: string, planDate: string, retake = false) => request<DailyReview>(`/api/daily-review/date/${planDate}/start${retake ? '?retake=true' : ''}`, { method: 'POST' }, token),
    answerDailyReview: (token: string, attemptId: string, questionId: string, optionId: string) => request<DailyReviewAnswer>(`/api/daily-review/${attemptId}/answer`, { method: 'POST', body: JSON.stringify({ question_id: questionId, selected_option_id: optionId }) }, token),
    dailyGrowth: (token: string) => request<DailyGrowth>('/api/daily-growth/today', {}, token),
    answerDailyVocabulary: (token: string, wordId: string, selectedOption: string) => request<VocabularyAnswer>('/api/daily-growth/vocabulary/answer', { method: 'POST', body: JSON.stringify({ word_id: wordId, selected_option: selectedOption }) }, token),
    todaySSBGuidance: (token: string) => request<DailySSBGuidance>('/api/ssb-guidance/today', {}, token),
    ssbGuidanceChat: (token: string) => request<{ messages: SSBGuidanceMessage[] }>('/api/ssb-guidance/chat', {}, token),
    sendSSBGuidanceMessage: (token: string, content: string) => request<SSBGuidanceMessage[]>('/api/ssb-guidance/chat', { method: 'POST', body: JSON.stringify({ content }) }, token),
}
