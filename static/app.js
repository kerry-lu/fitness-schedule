let token = localStorage.getItem('token');
let currentUser = null;
let calendar = null;
let students = [];
let courses = [];
let templates = [];
let coaches = [];
let currentScheduleId = null;

// HTML 转义函数，防止 XSS
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// HTML 属性转义函数
function escapeAttr(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// Toast 通知系统
let toastTimeout = null;
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    // 触发动画
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // 自动移除
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
    return container;
}

// 添加 toast 样式
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast {
        padding: 12px 20px;
        border-radius: 8px;
        color: #fff;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        max-width: 300px;
    }
    .toast.show {
        opacity: 1;
        transform: translateX(0);
    }
    .toast-info { background: #3b82f6; }
    .toast-success { background: #22c55e; }
    .toast-error { background: #ef4444; }
    .toast-warning { background: #f59e0b; }
`;
document.head.appendChild(toastStyles);

// ==================== 初始化 ====================

async function checkAuth() {
    if (!token) {
        window.location.href = '/login';
        return false;
    }

    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error();
        currentUser = await response.json();
        document.getElementById('user-name').textContent = currentUser.name;
        return true;
    } catch {
        logout();
        return false;
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

function toggleSidebar() {
    // Sidebar removed - no-op
}

function toggleManagement() {
    // Management sidebar removed - no-op
}

function closeSidebarIfMobile() {
    // Sidebar removed - no-op
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers
        }
    });

    if (response.status === 401) {
        logout();
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '请求失败');
    }

    return response.json();
}

// ==================== 模板管理 ====================

async function loadTemplates() {
    templates = await apiRequest('/api/templates');
    renderTemplateList();
    updateTemplateSelect();
}

function renderTemplateList() {
    const list = document.getElementById('template-list');
    if (!list) return;
    list.innerHTML = templates.map(t => `
        <li onclick="editTemplate(${t.id})">
            <span>${escapeHtml(t.name)}</span>
            <span class="delete-btn" onclick="event.stopPropagation(); confirmDeleteTemplate(${t.id})">删除</span>
        </li>
    `).join('');
}

function updateTemplateSelect() {
    const select = document.getElementById('schedule-template');
    select.innerHTML = '<option value="">无</option>' + templates.map(t =>
        `<option value="${t.id}">${escapeHtml(t.name)}</option>`
    ).join('');
}

function showTemplateModal(id = null) {
    document.getElementById('template-modal').classList.add('active');
    document.getElementById('template-form').reset();
    document.getElementById('template-id').value = '';
    document.getElementById('delete-template-btn').style.display = 'none';
    document.getElementById('template-modal-title').textContent = '新增模板';
    document.getElementById('template-stages').innerHTML = '';

    if (id) {
        editTemplate(id);
    } else {
        addTemplateStage();
    }
}

function editTemplate(id) {
    // 确保 id 是数字类型
    id = parseInt(id);
    const template = templates.find(t => t.id === id);
    if (!template) {
        alert('模板不存在或已删除');
        loadTemplates();
        return;
    }

    document.getElementById('template-modal').classList.add('active');
    document.getElementById('template-id').value = template.id;
    document.getElementById('template-name').value = template.name;
    document.getElementById('template-modal-title').textContent = '编辑模板';
    document.getElementById('delete-template-btn').style.display = 'block';

    // 解析并渲染训练内容
    try {
        const content = JSON.parse(template.content || '{"stages":[]}');
        document.getElementById('template-stages').innerHTML = '';

        if (content.stages && content.stages.length > 0) {
            content.stages.forEach(stage => addTemplateStage(stage));
        } else {
            addTemplateStage();
        }
    } catch (e) {
        document.getElementById('template-stages').innerHTML = '';
        addTemplateStage();
    }
}

function addTemplateStage(stage = null) {
    const container = document.getElementById('template-stages');
    const stageDiv = document.createElement('div');
    stageDiv.className = 'template-stage-editor';

    let exercisesHtml = '';
    if (stage?.exercises && stage.exercises.length > 0) {
        exercisesHtml = stage.exercises.map((ex, idx) => `
            <div class="exercise-row" data-index="${idx}">
                <input type="text" class="exercise-name" placeholder="动作名称" value="${escapeAttr(ex.name || '')}">
                <input type="number" class="exercise-sets" placeholder="组" value="${escapeAttr(ex.sets || '')}" min="1" style="width: 60px;">
                <span class="exercise-unit">组 ×</span>
                <input type="number" class="exercise-reps" placeholder="次" value="${escapeAttr(ex.reps || '')}" min="1" style="width: 60px;">
                <span class="exercise-unit">次</span>
                <button type="button" class="exercise-remove" onclick="removeExerciseRow(this)">×</button>
            </div>
        `).join('');
    } else {
        exercisesHtml = getEmptyExerciseRow();
    }

    stageDiv.innerHTML = `
        <div class="template-stage-header-editor">
            <input type="text" class="stage-name" placeholder="阶段名称（如：热身）" value="${escapeAttr(stage?.name || '')}" required>
            <input type="number" class="stage-duration" placeholder="时长" value="${escapeAttr(stage?.duration || '')}" style="width: 70px;">
            <span class="exercise-unit">分钟</span>
        </div>
        <div class="template-exercises-list">
            ${exercisesHtml}
        </div>
        <button type="button" onclick="addExerciseRow(this)" class="btn btn-secondary btn-small" style="margin-top: 8px;">+ 添加动作</button>
        <button type="button" onclick="this.parentElement.remove()" class="btn btn-danger btn-small" style="margin-top: 8px; margin-left: 8px;">删除阶段</button>
    `;
    container.appendChild(stageDiv);
}

function getEmptyExerciseRow() {
    return `
        <div class="exercise-row">
            <input type="text" class="exercise-name" placeholder="动作名称" value="">
            <input type="number" class="exercise-sets" placeholder="组" value="" min="1" style="width: 60px;">
            <span class="exercise-unit">组 ×</span>
            <input type="number" class="exercise-reps" placeholder="次" value="" min="1" style="width: 60px;">
            <span class="exercise-unit">次</span>
            <button type="button" class="exercise-remove" onclick="removeExerciseRow(this)">×</button>
        </div>
    `;
}

function addExerciseRow(btn) {
    const exercisesList = btn.previousElementSibling;
    const newRow = document.createElement('div');
    newRow.className = 'exercise-row';
    newRow.innerHTML = getEmptyExerciseRow();
    exercisesList.appendChild(newRow);
}

function removeExerciseRow(btn) {
    const row = btn.parentElement;
    const exercisesList = row.parentElement;
    if (exercisesList.querySelectorAll('.exercise-row').length > 1) {
        row.remove();
    } else {
        row.querySelectorAll('input').forEach(input => input.value = '');
    }
}

async function saveTemplate(e) {
    e.preventDefault();
    const id = document.getElementById('template-id').value;

    // 收集阶段数据
    const stages = [];
    document.querySelectorAll('.template-stage-editor').forEach(editor => {
        const name = editor.querySelector('.stage-name').value.trim();
        const duration = parseInt(editor.querySelector('.stage-duration').value) || 0;

        const exercises = [];
        editor.querySelectorAll('.exercise-row').forEach(row => {
            const exerciseName = row.querySelector('.exercise-name').value.trim();
            const sets = parseInt(row.querySelector('.exercise-sets').value) || null;
            const reps = parseInt(row.querySelector('.exercise-reps').value) || null;

            if (exerciseName) {
                exercises.push({ name: exerciseName, sets, reps });
            }
        });

        if (name || exercises.length > 0) {
            stages.push({ name, duration, exercises });
        }
    });

    const data = {
        name: document.getElementById('template-name').value,
        content: JSON.stringify({ stages })
    };

    try {
        if (id) {
            await apiRequest(`/api/templates/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        } else {
            await apiRequest('/api/templates', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        closeModal('template-modal');
        loadTemplates();
        // 如果是从详情面板编辑的模板，刷新日历以显示更新后的内容
        if (window.currentDetailScheduleId) {
            refreshCalendar();
        }
    } catch (err) {
        alert(err.message);
    }
}

async function deleteTemplate() {
    const id = document.getElementById('template-id').value;
    if (!id) return;

    if (!confirm('确定要删除这个模板吗？')) return;

    try {
        await apiRequest(`/api/templates/${id}`, { method: 'DELETE' });
        closeModal('template-modal');
        loadTemplates();
    } catch (err) {
        alert(err.message);
    }
}

function confirmDeleteTemplate(id) {
    if (confirm('确定要删除这个模板吗？')) {
        deleteTemplateById(id);
    }
}

async function deleteTemplateById(id) {
    try {
        await apiRequest(`/api/templates/${id}`, { method: 'DELETE' });
        loadTemplates();
    } catch (err) {
        alert(err.message);
    }
}

// ==================== 教练管理 ====================

async function loadCoaches() {
    // 所有教练都能看到教练筛选
    try {
        coaches = await apiRequest('/api/coaches');
        updateCoachFilter();
    } catch (err) {
        // 如果是普通教练无法访问 coaches API，使用本地用户信息
        coaches = [currentUser];
        updateCoachFilter();
    }

    // 只有主教练能看到教练管理模块（检查元素是否存在）
    const coachSection = document.getElementById('coach-section');
    if (coachSection) {
        if (currentUser?.role !== 'head_coach') {
            coachSection.style.display = 'none';
        } else {
            coachSection.style.display = 'block';
            renderCoachList();
        }
    }
}

function updateCoachFilter() {
    const filterCoach = document.getElementById('filter-coach');
    filterCoach.innerHTML = '<option value="">全部教练</option>' + coaches.map(c =>
        `<option value="${c.id}">${escapeHtml(c.name)}${c.role === 'head_coach' ? ' (主教练)' : ''}</option>`
    ).join('');
}

function updateCoachSelect() {
    const coachSelect = document.getElementById('schedule-coach');
    if (!coachSelect) return;
    coachSelect.innerHTML = '<option value="">当前账号</option>' + coaches.map(c =>
        `<option value="${c.id}">${escapeHtml(c.name)}${c.role === 'head_coach' ? ' (主教练)' : ''}</option>`
    ).join('');
}

function renderCoachList() {
    const list = document.getElementById('coach-list');
    list.innerHTML = coaches.map(c => {
        const roleText = c.role === 'head_coach' ? '主教练' : '教练';
        const isCurrentUser = c.id === currentUser.id;
        return `
            <li onclick="${isCurrentUser ? '' : `editCoach(${c.id})`}">
                <span>${escapeHtml(c.name)} <small style="color: var(--ios-text-secondary);">(${roleText})</small></span>
                ${isCurrentUser ? '<small style="color: var(--ios-text-secondary);">当前</small>' : ''}
            </li>
        `;
    }).join('');
}

function editCoach(id) {
    const coach = coaches.find(c => c.id === id);
    if (!coach) return;

    document.getElementById('coach-modal').classList.add('active');
    document.getElementById('coach-id').value = coach.id;
    document.getElementById('coach-name').value = coach.name;
    document.getElementById('coach-role').value = coach.role;
}

async function saveCoach(e) {
    e.preventDefault();
    const id = document.getElementById('coach-id').value;
    const role = document.getElementById('coach-role').value;

    try {
        await apiRequest(`/api/coaches/${id}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role })
        });
        closeModal('coach-modal');
        loadCoaches();
    } catch (err) {
        alert(err.message);
    }
}

// ==================== 学员管理 ====================

async function loadStudents() {
    students = await apiRequest('/api/students');
    renderStudentList();
    updateStudentSelect();
}

function renderStudentList() {
    const list = document.getElementById('student-list');
    if (!list) return;

    // 按专项分组
    const groups = {};
    const noSpecialty = [];

    students.forEach(s => {
        if (s.specialty && s.specialty.trim()) {
            if (!groups[s.specialty]) {
                groups[s.specialty] = [];
            }
            groups[s.specialty].push(s);
        } else {
            noSpecialty.push(s);
        }
    });

    let html = '';

    // 渲染有专项的分组
    Object.keys(groups).sort().forEach(specialty => {
        html += `<li class="group-header">${escapeHtml(specialty)}</li>`;
        groups[specialty].forEach(s => {
            html += renderStudentItem(s);
        });
    });

    // 渲染无专项的学员
    if (noSpecialty.length > 0) {
        if (Object.keys(groups).length > 0) {
            html += `<li class="group-header">未分类</li>`;
        }
        noSpecialty.forEach(s => {
            html += renderStudentItem(s);
        });
    }

    if (students.length === 0) {
        html = '<li class="empty-tip">暂无学员</li>';
    }

    list.innerHTML = html;
}

function renderStudentItem(s) {
    let creditInfo = '';
    if (s.enable_credits) {
        const isLow = s.remaining_hours <= 3 && s.remaining_hours > 0;
        const isEmpty = s.remaining_hours <= 0;
        const creditClass = isEmpty ? 'credit-empty' : (isLow ? 'credit-low' : '');
        creditInfo = `<span class="credit-badge ${creditClass}">${Math.round(s.remaining_hours)}/${s.total_hours}</span>`;
    }
    let infoBadges = '';
    if (s.gender) infoBadges += `<span class="info-badge">${escapeHtml(s.gender)}</span>`;
    return `
        <li onclick="editStudent(${s.id})">
            <span>${escapeHtml(s.name)}${creditInfo}${infoBadges}</span>
            <span class="delete-btn" onclick="event.stopPropagation(); confirmDeleteStudent(${s.id})">删除</span>
        </li>
    `;
}

function updateStudentSelect() {
    const select = document.getElementById('schedule-student');
    select.innerHTML = students.map(s =>
        `<option value="${s.id}">${escapeHtml(s.name)}</option>`
    ).join('');

    // 更新筛选下拉框
    const filterStudent = document.getElementById('filter-student');
    filterStudent.innerHTML = '<option value="">全部学员</option>' + students.map(s =>
        `<option value="${s.id}">${escapeHtml(s.name)}</option>`
    ).join('');
}

function showStudentModal(id = null) {
    document.getElementById('student-modal').classList.add('active');
    document.getElementById('student-form').reset();
    document.getElementById('student-id').value = '';
    document.getElementById('student-name').value = '';
    document.getElementById('student-phone').value = '';
    document.getElementById('student-gender').value = '';
    document.getElementById('student-age').value = '';
    document.getElementById('student-specialty').value = '';
    document.getElementById('student-rehabilitation').value = '';
    document.getElementById('student-note').value = '';
    document.getElementById('student-enable-credits').checked = false;
    document.getElementById('credit-fields').style.display = 'none';
    document.getElementById('student-total-hours').value = 0;
    document.getElementById('student-remaining-hours').value = 0;
    document.getElementById('student-expiration-date').value = '';
    document.getElementById('delete-student-btn').style.display = 'none';
    document.getElementById('student-modal-title').textContent = '新增学员';

    // 监听课时开关
    document.getElementById('student-enable-credits').onchange = function() {
        document.getElementById('credit-fields').style.display = this.checked ? 'block' : 'none';
    };

    if (id) {
        editStudent(id);
    }
}

async function editStudent(id) {
    const student = students.find(s => s.id === id);
    if (!student) return;

    document.getElementById('student-modal').classList.add('active');
    document.getElementById('student-id').value = student.id;
    document.getElementById('student-name').value = student.name;
    document.getElementById('student-phone').value = student.phone || '';
    document.getElementById('student-gender').value = student.gender || '';
    document.getElementById('student-age').value = student.age || '';
    document.getElementById('student-specialty').value = student.specialty || '';
    document.getElementById('student-rehabilitation').value = student.rehabilitation || '';
    document.getElementById('student-note').value = student.note || '';
    document.getElementById('student-enable-credits').checked = student.enable_credits === 1;
    document.getElementById('credit-fields').style.display = student.enable_credits === 1 ? 'block' : 'none';
    document.getElementById('student-total-hours').value = student.total_hours || 0;
    document.getElementById('student-remaining-hours').value = student.remaining_hours || 0;
    document.getElementById('student-expiration-date').value = student.expiration_date || '';
    document.getElementById('student-modal-title').textContent = '编辑学员';
    document.getElementById('delete-student-btn').style.display = 'block';

    // 监听课时开关
    document.getElementById('student-enable-credits').onchange = function() {
        document.getElementById('credit-fields').style.display = this.checked ? 'block' : 'none';
    };
}

async function saveStudent(e) {
    e.preventDefault();
    const id = document.getElementById('student-id').value;
    const enableCredits = document.getElementById('student-enable-credits').checked;
    const data = {
        name: document.getElementById('student-name').value,
        phone: document.getElementById('student-phone').value,
        gender: document.getElementById('student-gender').value || null,
        age: parseInt(document.getElementById('student-age').value) || null,
        specialty: document.getElementById('student-specialty').value || null,
        rehabilitation: document.getElementById('student-rehabilitation').value || null,
        note: document.getElementById('student-note').value,
        enable_credits: enableCredits ? 1 : 0,
        total_hours: parseInt(document.getElementById('student-total-hours').value) || 0,
        remaining_hours: parseInt(document.getElementById('student-remaining-hours').value) || 0,
        expiration_date: document.getElementById('student-expiration-date').value || null
    };

    try {
        if (id) {
            await apiRequest(`/api/students/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        } else {
            await apiRequest('/api/students', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        closeModal('student-modal');
        loadStudents();
    } catch (err) {
        alert(err.message);
    }
}

async function deleteStudent() {
    const id = document.getElementById('student-id').value;
    if (!id) return;

    if (!confirm('确定要删除这个学员吗？')) return;

    try {
        await apiRequest(`/api/students/${id}`, { method: 'DELETE' });
        closeModal('student-modal');
        loadStudents();
    } catch (err) {
        alert(err.message);
    }
}

function confirmDeleteStudent(id) {
    if (confirm('确定要删除这个学员吗？')) {
        deleteStudentById(id);
    }
}

async function deleteStudentById(id) {
    try {
        await apiRequest(`/api/students/${id}`, { method: 'DELETE' });
        loadStudents();
    } catch (err) {
        alert(err.message);
    }
}

// ==================== 课程管理 ====================

async function loadCourses() {
    courses = await apiRequest('/api/courses');
    renderCourseList();
    updateCourseSelect();
}

function renderCourseList() {
    const list = document.getElementById('course-list');
    if (!list) return;
    list.innerHTML = courses.map(c => `
        <li onclick="editCourse(${c.id})">
            <span>${escapeHtml(c.name)} (${c.duration_minutes}分钟)</span>
            <span class="delete-btn" onclick="event.stopPropagation(); confirmDeleteCourse(${c.id})">删除</span>
        </li>
    `).join('');
}

function updateCourseSelect() {
    const select = document.getElementById('schedule-course');
    select.innerHTML = courses.map(c =>
        `<option value="${c.id}">${escapeHtml(c.name)} (${c.duration_minutes}分钟)</option>`
    ).join('');

    // 更新筛选下拉框
    const filterCourse = document.getElementById('filter-course');
    filterCourse.innerHTML = '<option value="">全部课程</option>' + courses.map(c =>
        `<option value="${c.id}">${escapeHtml(c.name)}</option>`
    ).join('');
}

function showCourseModal(id = null) {
    document.getElementById('course-modal').classList.add('active');
    document.getElementById('course-form').reset();
    document.getElementById('course-id').value = '';
    document.getElementById('delete-course-btn').style.display = 'none';
    document.getElementById('course-modal-title').textContent = '新增课程';

    if (id) {
        editCourse(id);
    }
}

async function editCourse(id) {
    const course = courses.find(c => c.id === id);
    if (!course) return;

    document.getElementById('course-modal').classList.add('active');
    document.getElementById('course-id').value = course.id;
    document.getElementById('course-name').value = course.name;
    document.getElementById('course-duration').value = course.duration_minutes;
    document.getElementById('course-description').value = course.description || '';
    document.getElementById('course-modal-title').textContent = '编辑课程';
    document.getElementById('delete-course-btn').style.display = 'block';
}

async function saveCourse(e) {
    e.preventDefault();
    const id = document.getElementById('course-id').value;
    const data = {
        name: document.getElementById('course-name').value,
        duration_minutes: parseInt(document.getElementById('course-duration').value),
        description: document.getElementById('course-description').value
    };

    try {
        if (id) {
            await apiRequest(`/api/courses/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        } else {
            await apiRequest('/api/courses', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        closeModal('course-modal');
        loadCourses();
    } catch (err) {
        alert(err.message);
    }
}

async function deleteCourse() {
    const id = document.getElementById('course-id').value;
    if (!id) return;

    if (!confirm('确定要删除这个课程吗？')) return;

    try {
        await apiRequest(`/api/courses/${id}`, { method: 'DELETE' });
        closeModal('course-modal');
        loadCourses();
    } catch (err) {
        alert(err.message);
    }
}

function confirmDeleteCourse(id) {
    if (confirm('确定要删除这个课程吗？')) {
        deleteCourseById(id);
    }
}

async function deleteCourseById(id) {
    try {
        await apiRequest(`/api/courses/${id}`, { method: 'DELETE' });
        loadCourses();
    } catch (err) {
        alert(err.message);
    }
}

// ==================== 课表管理 ====================

function initTimeSelect() {
    const select = document.getElementById('schedule-start-time');
    select.innerHTML = '';
    for (let h = 10; h <= 20; h++) {
        for (let m = 0; m < 60; m += 30) {
            const hour = h.toString().padStart(2, '0');
            const minute = m.toString().padStart(2, '0');
            const time = `${hour}:${minute}`;
            const option = document.createElement('option');
            option.value = time;
            option.textContent = time;
            select.appendChild(option);
        }
    }
}

function showScheduleModal(dateStr = null, scheduleId = null, time = null) {
    document.getElementById('schedule-modal').classList.add('active');
    document.getElementById('schedule-form').reset();
    document.getElementById('schedule-id').value = '';
    document.getElementById('delete-schedule-btn').style.display = 'none';
    document.getElementById('schedule-modal-title').textContent = '新增课程安排';
    document.getElementById('schedule-repeat-type').value = 'none';
    document.getElementById('repeat-end-date-container').style.display = 'none';
    document.getElementById('schedule-repeat-end-date').value = '';
    document.getElementById('repeat-days-container').style.display = 'none';

    // 重置重复选项
    document.querySelectorAll('.repeat-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.repeat === 'none');
    });

    // 重置周几选项
    document.querySelectorAll('.repeat-day').forEach(cb => cb.checked = false);

    // 确保模板下拉框已填充
    updateTemplateSelect();

    // 更新教练下拉框并默认选择当前账号
    updateCoachSelect();
    document.getElementById('schedule-coach').value = currentUser?.id || '';

    initTimeSelect();

    if (dateStr) {
        document.getElementById('schedule-date').value = dateStr;
    } else {
        document.getElementById('schedule-date').value = new Date().toISOString().split('T')[0];
    }

    if (time) {
        document.getElementById('schedule-start-time').value = time;
    }

    if (scheduleId) {
        editSchedule(scheduleId);
    }
}

async function editSchedule(id) {
    try {
        const schedule = await apiRequest(`/api/schedules/${id}`);

        document.getElementById('schedule-modal').classList.add('active');
        document.getElementById('schedule-id').value = schedule.id;
        document.getElementById('schedule-date').value = schedule.date;
        document.getElementById('schedule-student').value = schedule.student_id;
        document.getElementById('schedule-course').value = schedule.course_id;
        document.getElementById('schedule-template').value = schedule.template_id || '';
        document.getElementById('schedule-note').value = schedule.note || '';

        // 教练选择
        updateCoachSelect();
        document.getElementById('schedule-coach').value = schedule.user_id || '';

        initTimeSelect();
        const startTime = schedule.start_time.substring(0, 5);
        document.getElementById('schedule-start-time').value = startTime;

        // 重复设置
        const repeatType = schedule.repeat_type || 'none';
        document.getElementById('schedule-repeat-type').value = repeatType;
        document.querySelectorAll('.repeat-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.repeat === repeatType);
        });
        document.getElementById('repeat-end-date-container').style.display =
            repeatType !== 'none' ? 'block' : 'none';
        document.getElementById('schedule-repeat-end-date').value =
            schedule.repeat_end_date || '';

        // 周几选项
        document.getElementById('repeat-days-container').style.display =
            repeatType === 'weekly' ? 'block' : 'none';
        // 重置并设置周几选项
        document.querySelectorAll('.repeat-day').forEach(cb => cb.checked = false);
        if (schedule.repeat_days) {
            try {
                const days = JSON.parse(schedule.repeat_days);
                days.forEach(day => {
                    const cb = document.querySelector(`.repeat-day[value="${day}"]`);
                    if (cb) cb.checked = true;
                });
            } catch (e) {}
        }

        document.getElementById('schedule-modal-title').textContent = '编辑课程安排';
        document.getElementById('delete-schedule-btn').style.display = 'block';
    } catch (err) {
        alert(err.message);
    }
}

async function saveSchedule(e) {
    e.preventDefault();
    const id = document.getElementById('schedule-id').value;

    // 获取周几选择
    const repeatDays = [];
    document.querySelectorAll('.repeat-day:checked').forEach(cb => {
        repeatDays.push(parseInt(cb.value));
    });

    const coachId = document.getElementById('schedule-coach').value;
    const data = {
        student_id: parseInt(document.getElementById('schedule-student').value),
        course_id: parseInt(document.getElementById('schedule-course').value),
        coach_id: coachId ? parseInt(coachId) : null,
        date: document.getElementById('schedule-date').value,
        start_time: document.getElementById('schedule-start-time').value,
        note: document.getElementById('schedule-note').value,
        template_id: document.getElementById('schedule-template').value || null,
        repeat_type: document.getElementById('schedule-repeat-type').value,
        repeat_end_date: document.getElementById('schedule-repeat-end-date').value || null,
        repeat_days: repeatDays.length > 0 ? JSON.stringify(repeatDays) : null
    };

    try {
        if (id) {
            // 使用 PUT 更新
            await apiRequest(`/api/schedules/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        } else {
            // 使用 POST 创建
            await apiRequest('/api/schedules', {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        closeModal('schedule-modal');
        refreshCalendar();
    } catch (err) {
        alert(err.message);
    }
}

async function deleteSchedule() {
    const id = document.getElementById('schedule-id').value;
    if (!id) return;

    if (!confirm('确定要删除这个课程安排吗？')) return;

    try {
        await apiRequest(`/api/schedules/${id}`, { method: 'DELETE' });
        closeModal('schedule-modal');
        closeDetailPanel();
        refreshCalendar();
    } catch (err) {
        alert(err.message);
    }
}

// ==================== 右侧详情面板 ====================

async function showDetailPanel(scheduleId) {
    currentScheduleId = scheduleId;
    const panel = document.getElementById('detail-panel');

    try {
        const schedule = await apiRequest(`/api/schedules/${scheduleId}`);

        document.getElementById('detail-student').textContent =
            schedule.student?.name || '未知';
        document.getElementById('detail-course').textContent =
            schedule.course?.name || '未知';
        document.getElementById('detail-coach').textContent =
            schedule.coach?.name || (schedule.user_id ? `教练 #${schedule.user_id}` : '未知');

        const date = new Date(schedule.date);
        document.getElementById('detail-date').textContent =
            date.toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        document.getElementById('detail-time').textContent =
            `${schedule.start_time.substring(0, 5)} - ${schedule.end_time.substring(0, 5)}`;

        document.getElementById('detail-note-input').value =
            schedule.note || '';

        // 填充模板下拉框
        const templateSelect = document.getElementById('detail-template-select');
        templateSelect.innerHTML = '<option value="">无</option>' + templates.map(t =>
            `<option value="${t.id}">${escapeHtml(t.name)}</option>`
        ).join('');
        templateSelect.value = schedule.template_id || '';

        // 渲染训练内容（优先使用课程安排自己的训练内容，否则使用模板内容）
        const trainingContent = schedule.training_content || (schedule.template ? schedule.template.content : null);
        renderTrainingContent(trainingContent);
        // 存储当前课程安排的训练内容供编辑使用
        window.currentScheduleTrainingContent = trainingContent;

        // 显示上课记录
        const attendanceSection = document.getElementById('attendance-section');
        const btnComplete = document.getElementById('btn-complete');
        if (schedule.attendance_record) {
            attendanceSection.style.display = 'block';
            btnComplete.style.display = 'none';

            // 状态显示
            const statusMap = { 'completed': '已完成', 'absent': '缺席', 'cancelled': '已取消' };
            document.getElementById('detail-attendance-status').textContent =
                statusMap[schedule.attendance_record.status] || schedule.attendance_record.status;

            // 学员状态
            const studentStatusRow = document.getElementById('detail-attendance-student-status-row');
            if (schedule.attendance_record.student_status) {
                studentStatusRow.style.display = 'block';
                document.getElementById('detail-attendance-student-status').textContent =
                    schedule.attendance_record.student_status;
            } else {
                studentStatusRow.style.display = 'none';
            }

            // 教练备注
            const noteRow = document.getElementById('detail-attendance-note-row');
            if (schedule.attendance_record.coach_note) {
                noteRow.style.display = 'block';
                document.getElementById('detail-attendance-note').textContent =
                    schedule.attendance_record.coach_note;
            } else {
                noteRow.style.display = 'none';
            }
        } else {
            attendanceSection.style.display = 'none';
            btnComplete.style.display = 'inline-block';
        }

        // 确保训练内容编辑是隐藏状态
        document.getElementById('training-edit-section').style.display = 'none';
        document.getElementById('training-view-section').style.display = 'block';

        // 切换到详情视图
        document.getElementById('schedule-list-view').style.display = 'none';
        document.getElementById('schedule-detail-view').style.display = 'block';
        document.getElementById('detail-panel-title').textContent = '课程详情';
    } catch (err) {
        alert(err.message);
    }
}

function showScheduleList() {
    currentScheduleId = null;
    document.getElementById('schedule-list-view').style.display = 'block';
    document.getElementById('schedule-detail-view').style.display = 'none';
    document.getElementById('detail-panel-title').textContent = '日程列表';
    loadScheduleList();
}

async function applyTemplateFromPanel() {
    if (!currentScheduleId) return;
    const templateId = document.getElementById('detail-template-select').value;

    try {
        await apiRequest(`/api/schedules/${currentScheduleId}`, {
            method: 'PUT',
            body: JSON.stringify({ template_id: templateId || null })
        });
        // 刷新详情显示
        showDetailPanel(currentScheduleId);
        refreshCalendar();
    } catch (err) {
        alert(err.message);
    }
}

async function saveNoteFromPanel() {
    if (!currentScheduleId) return;
    const note = document.getElementById('detail-note-input').value;

    try {
        await apiRequest(`/api/schedules/${currentScheduleId}`, {
            method: 'PUT',
            body: JSON.stringify({ note })
        });
        alert('备注已保存');
    } catch (err) {
        alert(err.message);
    }
}

function loadScheduleList() {
    const container = document.getElementById('schedule-list-content');
    const today = new Date().toISOString().split('T')[0];

    apiRequest(`/api/schedules?start_date=${today}&end_date=${today}`).then(schedules => {
        if (schedules.length === 0) {
            container.innerHTML = '<p style="color: var(--ios-text-secondary); text-align: center; padding: 20px;">今日暂无课程</p>';
            return;
        }

        container.innerHTML = schedules.map(s => `
            <div class="schedule-list-item" onclick="showDetailPanel(${s.id})">
                <div class="schedule-list-time">${s.start_time.substring(0, 5)} - ${s.end_time.substring(0, 5)}</div>
                <div class="schedule-list-info">
                    <div class="schedule-list-student">${escapeHtml(s.student?.name || '未知')}</div>
                    <div class="schedule-list-course">${escapeHtml(s.course?.name || '未知')}</div>
                </div>
            </div>
        `).join('');
    });
}

function closeDetailPanel() {
    currentScheduleId = null;
    // 重置为列表视图
    showScheduleList();
}

function renderTemplateContent(template) {
    const container = document.getElementById('detail-template');

    if (!template || !template.content) {
        container.innerHTML = '<p style="color: var(--ios-text-secondary);">暂无训练内容</p>';
        return;
    }

    try {
        const content = JSON.parse(template.content);
        if (!content.stages || content.stages.length === 0) {
            container.innerHTML = '<p style="color: var(--ios-text-secondary);">暂无训练内容</p>';
            return;
        }

        container.innerHTML = content.stages.map(stage => `
            <div class="template-stage">
                <div class="template-stage-header">
                    <span class="template-stage-name">${escapeHtml(stage.name || '未命名阶段')}</span>
                    <span class="template-stage-duration">${stage.duration || 0}分钟</span>
                </div>
                ${stage.exercises?.map(ex => {
                    if (typeof ex === 'string') {
                        return `<div class="template-exercise">${escapeHtml(ex)}</div>`;
                    }
                    const sets = ex.sets ? `${ex.sets}组` : '';
                    const reps = ex.reps ? `${ex.reps}次` : '';
                    // 先数量后组数
                    const detail = [reps, sets].filter(Boolean).join(' × ');
                    return `<div class="template-exercise">${escapeHtml(ex.name)}${detail ? ` (${detail})` : ''}</div>`;
                }).join('') || ''}
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p style="color: var(--ios-text-secondary);">训练内容格式错误</p>';
    }
}

function renderTrainingContent(contentStr) {
    const container = document.getElementById('detail-training');

    if (!contentStr) {
        container.innerHTML = '<p style="color: var(--ios-text-secondary);">暂无训练内容</p>';
        return;
    }

    try {
        const content = JSON.parse(contentStr);
        if (!content.stages || content.stages.length === 0) {
            container.innerHTML = '<p style="color: var(--ios-text-secondary);">暂无训练内容</p>';
            return;
        }

        container.innerHTML = content.stages.map(stage => `
            <div class="template-stage">
                <div class="template-stage-header">
                    <span class="template-stage-name">${escapeHtml(stage.name || '未命名阶段')}</span>
                    <span class="template-stage-duration">${stage.duration || 0}分钟</span>
                </div>
                ${stage.exercises?.map(ex => {
                    if (typeof ex === 'string') {
                        return `<div class="template-exercise">${escapeHtml(ex)}</div>`;
                    }
                    const sets = ex.sets ? `${ex.sets}组` : '';
                    const reps = ex.reps ? `${ex.reps}次` : '';
                    const detail = [reps, sets].filter(Boolean).join(' × ');
                    return `<div class="template-exercise">${escapeHtml(ex.name)}${detail ? ` (${detail})` : ''}</div>`;
                }).join('') || ''}
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<p style="color: var(--ios-text-secondary);">训练内容格式错误</p>';
    }
}

function showTrainingEdit() {
    if (!currentScheduleId) return;

    // 隐藏查看模式，显示编辑模式
    document.getElementById('training-view-section').style.display = 'none';
    document.getElementById('training-edit-section').style.display = 'block';

    // 解析当前训练内容
    let content = { stages: [] };
    if (window.currentScheduleTrainingContent) {
        try {
            content = JSON.parse(window.currentScheduleTrainingContent);
        } catch (e) {
            content = { stages: [] };
        }
    }

    // 渲染训练阶段编辑器
    const container = document.getElementById('training-edit-stages');
    container.innerHTML = '';
    if (content.stages && content.stages.length > 0) {
        content.stages.forEach(stage => addTrainingStageEdit(stage));
    } else {
        addTrainingStageEdit();
    }
}

function cancelTrainingEdit() {
    // 隐藏编辑模式，显示查看模式
    document.getElementById('training-edit-section').style.display = 'none';
    document.getElementById('training-view-section').style.display = 'block';
}

function addTrainingStageEdit(stage = null) {
    const container = document.getElementById('training-edit-stages');
    const stageDiv = document.createElement('div');
    stageDiv.className = 'template-stage-editor';

    let exercisesHtml = '';
    if (stage?.exercises && stage.exercises.length > 0) {
        exercisesHtml = stage.exercises.map((ex, idx) => `
            <div class="exercise-row">
                <input type="text" class="exercise-name" placeholder="动作名称" value="${escapeAttr(ex.name || '')}">
                <input type="number" class="exercise-reps" placeholder="次" value="${escapeAttr(ex.reps || '')}" min="1" style="width: 60px;">
                <span class="exercise-unit">次 ×</span>
                <input type="number" class="exercise-sets" placeholder="组" value="${escapeAttr(ex.sets || '')}" min="1" style="width: 60px;">
                <span class="exercise-unit">组</span>
                <button type="button" class="exercise-remove" onclick="this.parentElement.remove()">×</button>
            </div>
        `).join('');
    } else {
        exercisesHtml = `
            <div class="exercise-row">
                <input type="text" class="exercise-name" placeholder="动作名称" value="">
                <input type="number" class="exercise-reps" placeholder="次" value="" min="1" style="width: 60px;">
                <span class="exercise-unit">次 ×</span>
                <input type="number" class="exercise-sets" placeholder="组" value="" min="1" style="width: 60px;">
                <span class="exercise-unit">组</span>
                <button type="button" class="exercise-remove" onclick="this.parentElement.remove()">×</button>
            </div>
        `;
    }

    stageDiv.innerHTML = `
        <div class="template-stage-header-editor">
            <input type="text" class="stage-name" placeholder="阶段名称（如：热身）" value="${escapeAttr(stage?.name || '')}" style="flex:1;">
            <input type="number" class="stage-duration" placeholder="时长" value="${escapeAttr(stage?.duration || '')}" style="width: 70px;">
            <span class="exercise-unit">分钟</span>
            <button type="button" class="exercise-remove" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="template-exercises-list">
            ${exercisesHtml}
        </div>
        <button type="button" onclick="addExerciseRowToTraining(this)" class="btn btn-secondary btn-small" style="margin-top: 8px;">+ 添加动作</button>
    `;
    container.appendChild(stageDiv);
}

function addExerciseRowToTraining(btn) {
    const exercisesList = btn.previousElementSibling;
    const newRow = document.createElement('div');
    newRow.className = 'exercise-row';
    newRow.innerHTML = `
        <input type="text" class="exercise-name" placeholder="动作名称" value="">
        <input type="number" class="exercise-reps" placeholder="次" value="" min="1" style="width: 60px;">
        <span class="exercise-unit">次 ×</span>
        <input type="number" class="exercise-sets" placeholder="组" value="" min="1" style="width: 60px;">
        <span class="exercise-unit">组</span>
        <button type="button" class="exercise-remove" onclick="this.parentElement.remove()">×</button>
    `;
    exercisesList.appendChild(newRow);
}

async function saveTrainingContent() {
    if (!currentScheduleId) return;

    // 收集阶段数据
    const stages = [];
    document.querySelectorAll('#training-edit-stages .template-stage-editor').forEach(editor => {
        const name = editor.querySelector('.stage-name').value.trim();
        const duration = parseInt(editor.querySelector('.stage-duration').value) || 0;

        const exercises = [];
        editor.querySelectorAll('.exercise-row').forEach(row => {
            const exerciseName = row.querySelector('.exercise-name').value.trim();
            const reps = parseInt(row.querySelector('.exercise-reps').value) || null;
            const sets = parseInt(row.querySelector('.exercise-sets').value) || null;

            if (exerciseName) {
                exercises.push({ name: exerciseName, reps, sets });
            }
        });

        if (name || exercises.length > 0) {
            stages.push({ name, duration, exercises });
        }
    });

    const trainingContent = JSON.stringify({ stages });

    try {
        await apiRequest(`/api/schedules/${currentScheduleId}`, {
            method: 'PUT',
            body: JSON.stringify({ training_content: trainingContent })
        });

        cancelTrainingEdit();
        showDetailPanel(currentScheduleId);
    } catch (err) {
        alert(err.message);
    }
}

function editScheduleFromPanel() {
    if (currentScheduleId) {
        showScheduleModal(null, currentScheduleId);
    }
}

async function deleteScheduleFromPanel() {
    if (!currentScheduleId) return;

    try {
        const schedule = await apiRequest(`/api/schedules/${currentScheduleId}`);
        let deleteUrl = `/api/schedules/${currentScheduleId}`;
        let confirmMessage = '确定要删除这个课程安排吗？';

        if (schedule.series_id) {
            // 是系列课程，让用户选择删除方式
            const deleteAll = confirm('该课程属于一个重复系列。\n\n点击"确定"删除整个系列的所有课程\n点击"取消"只删除这一节');
            if (deleteAll) {
                deleteUrl = `/api/schedules/${currentScheduleId}/series`;
                confirmMessage = '确定要删除整个重复系列的所有课程吗？';
            }
        }

        if (!confirm(confirmMessage)) return;

        await apiRequest(deleteUrl, { method: 'DELETE' });
        closeDetailPanel();
        refreshCalendar();
    } catch (err) {
        alert(err.message);
    }
}

async function completeScheduleFromPanel() {
    if (!currentScheduleId) return;

    try {
        const schedule = await apiRequest(`/api/schedules/${currentScheduleId}`);
        document.getElementById('attendance-schedule-id').value = currentScheduleId;
        document.getElementById('attendance-student-id').value = schedule.student_id;
        document.getElementById('attendance-student-name').value = schedule.student?.name || '未知';
        document.getElementById('attendance-student-status').value = '';
        document.getElementById('attendance-coach-note').value = '';
        document.getElementById('attendance-deduct-credits').checked = true;
        document.getElementById('attendance-modal').classList.add('active');
    } catch (err) {
        alert(err.message);
    }
}

async function submitAttendance(e) {
    e.preventDefault();
    const scheduleId = document.getElementById('attendance-schedule-id').value;
    const studentId = document.getElementById('attendance-student-id').value;
    const studentStatus = document.getElementById('attendance-student-status').value;
    const coachNote = document.getElementById('attendance-coach-note').value;
    const deductCredits = document.getElementById('attendance-deduct-credits').checked;

    try {
        // 获取课程详情以获取日期
        const schedule = await apiRequest(`/api/schedules/${scheduleId}`);

        // 创建上课记录
        await apiRequest('/api/schedules/attendance', {
            method: 'POST',
            body: JSON.stringify({
                schedule_id: parseInt(scheduleId),
                student_id: parseInt(studentId),
                date: schedule.date,
                status: 'completed',
                student_status: studentStatus || null,
                coach_note: coachNote || null
            })
        });

        // 完成课程（扣减课时等）
        const result = await apiRequest(`/api/schedules/${scheduleId}/complete?deduct_credits=${deductCredits}`, {
            method: 'POST'
        });

        closeModal('attendance-modal');
        closeDetailPanel();
        refreshCalendar();
        loadStudents();
        alert(`课程已完成！剩余课时: ${Math.round(result.remaining_hours)}`);
    } catch (err) {
        alert(err.message);
    }
}

// ==================== 日历 ====================

function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        locale: 'zh-cn',
        buttonText: {
            today: '今天',
            month: '月',
            week: '周',
            day: '日'
        },
        editable: true,
        dateClick: function(info) {
            showQuickAddPanel(info.dateStr);
        },
        eventClick: function(info) {
            showDetailPanel(info.event.id);
        },
        eventDrop: function(info) {
            updateScheduleFromDrag(info.event);
        },
        eventResize: function(info) {
            updateScheduleFromDrag(info.event);
        },
        events: loadCalendarEvents,
        eventContent: function(arg) {
            const start = arg.event.start;
            const end = arg.event.end;
            let timeStr = '';
            if (start && end) {
                const startTime = start.toTimeString().substring(0, 5);
                const endTime = end.toTimeString().substring(0, 5);
                timeStr = `${startTime}-${endTime}`;
            } else {
                timeStr = arg.timeText;
            }
            // 检查是否有备注
            const hasNote = arg.event.extendedProps.note;
            const noteIcon = hasNote ? '<span style="color: var(--ios-orange); font-weight: bold; margin-left: 4px;">●</span>' : '';
            return {
                html: `<div class="fc-event-main-content">
                    <div class="fc-event-title">${arg.event.title}${noteIcon}</div>
                    <div class="fc-event-time">${timeStr}</div>
                </div>`
            };
        }
    });
    calendar.render();
}

async function updateScheduleFromDrag(eventEl) {
    const scheduleId = eventEl.id;
    const newDate = eventEl.startStr.split('T')[0];
    const newStartTime = eventEl.startStr.split('T')[1]?.substring(0, 5) || '09:00';

    try {
        await apiRequest(`/api/schedules/${scheduleId}/move`, {
            method: 'PUT',
            body: JSON.stringify({
                date: newDate,
                start_time: newStartTime
            })
        });
        refreshCalendar();
    } catch (err) {
        alert(err.message);
        refreshCalendar(); // 恢复原位
    }
}

function showQuickAddPanel(dateStr) {
    const panel = document.getElementById('quick-add-panel');
    panel.classList.add('active');
    document.getElementById('quick-add-date').value = dateStr;
    document.getElementById('slide-overlay').classList.add('active');
    renderQuickAddContent(dateStr);
}

function renderQuickAddContent(dateStr) {
    const container = document.getElementById('quick-add-content');
    const selectedDate = new Date(dateStr);

    apiRequest(`/api/schedules?start_date=${dateStr}&end_date=${dateStr}`).then(schedules => {
        // 计算每个时间点是否被占用（考虑课程时长）
        const bookedTimes = new Set();
        schedules.forEach(s => {
            const start = timeToMinutes(s.start_time.substring(0, 5));
            const end = timeToMinutes(s.end_time.substring(0, 5));
            // 标记从开始到结束的所有 30 分钟时段为已占用
            for (let t = start; t < end; t += 30) {
                bookedTimes.add(t);
            }
        });

        let html = `<div class="quick-add-section">
            <h4>${selectedDate.toLocaleDateString('zh-CN', {month:'long', day:'numeric', weekday:'long'})}</h4>
            <p class="quick-add-hint">点击时段可快速添加课程</p>
        </div>`;

        for (let h = 10; h <= 20; h++) {
            for (let m = 0; m < 60; m += 30) {
                const hour = h.toString().padStart(2, '0');
                const minute = m.toString().padStart(2, '0');
                const time = `${hour}:${minute}`;
                const timeMinutes = timeToMinutes(time);
                const isBooked = bookedTimes.has(timeMinutes);

                html += `<div class="time-slot ${isBooked ? 'booked' : ''}" onclick="quickAddSchedule('${dateStr}', '${time}', ${isBooked})">
                    <span class="time-slot-time">${time}</span>
                    <span class="time-slot-status">${isBooked ? '已预约' : '可预约'}</span>
                </div>`;
            }
        }

        container.innerHTML = html;
    });
}

function timeToMinutes(timeStr) {
    const [h, m] = timeStr.split(':').map(Number);
    return h * 60 + m;
}

function quickAddSchedule(date, time, isBooked) {
    if (isBooked) {
        apiRequest(`/api/schedules?start_date=${date}&end_date=${date}`).then(schedules => {
            const schedule = schedules.find(s => s.start_time.substring(0, 5) === time);
            if (schedule) {
                showDetailPanel(schedule.id);
            }
        });
    } else {
        closeQuickAddPanel();
        showScheduleModal(date, null, time);
    }
}

function closeQuickAddPanel() {
    document.getElementById('quick-add-panel').classList.remove('active');
    document.getElementById('slide-overlay').classList.remove('active');
}

async function loadCalendarEvents(info, successCallback, failureCallback) {
    try {
        const startDate = info.startStr.split('T')[0];
        const endDate = info.endStr.split('T')[0];

        const schedules = await apiRequest(
            `/api/schedules?start_date=${startDate}&end_date=${endDate}`
        );

        // 获取筛选条件
        const filterCoach = document.getElementById('filter-coach').value;
        const filterStudent = document.getElementById('filter-student').value;
        const filterCourse = document.getElementById('filter-course').value;

        // 过滤事件
        let filteredSchedules = schedules;
        if (filterCoach) {
            filteredSchedules = filteredSchedules.filter(s => s.user_id === parseInt(filterCoach));
        }
        if (filterStudent) {
            filteredSchedules = filteredSchedules.filter(s => s.student_id === parseInt(filterStudent));
        }
        if (filterCourse) {
            filteredSchedules = filteredSchedules.filter(s => s.course_id === parseInt(filterCourse));
        }

        const events = filteredSchedules.map(s => {
            const classes = [];
            if (s.repeat_type && s.repeat_type !== 'none') {
                classes.push('recurring');
            }
            if (s.template_id) {
                classes.push('has-template');
            }
            // 按教练区分颜色
            classes.push(`coach-${s.user_id}`);

            // 根据上课记录状态添加样式
            if (s.attendance_record) {
                if (s.attendance_record.status === 'completed') {
                    classes.push('status-completed');
                } else if (s.attendance_record.status === 'absent') {
                    classes.push('status-absent');
                } else if (s.attendance_record.status === 'cancelled') {
                    classes.push('status-cancelled');
                }
            }

            return {
                id: s.id,
                title: `${s.student?.name || '未知'} - ${s.course?.name || '未知'} [${s.coach?.name || '教练'}]`,
                start: `${s.date}T${s.start_time}`,
                end: `${s.date}T${s.end_time}`,
                extendedProps: {
                    student: s.student,
                    course: s.course,
                    coach: s.coach,
                    template: s.template,
                    note: s.note,
                    repeatType: s.repeat_type,
                    userId: s.user_id
                },
                classNames: classes
            };
        });

        successCallback(events);
    } catch (err) {
        failureCallback(err);
    }
}

function refreshCalendar() {
    calendar.refetchEvents();
}

function applyFilters() {
    refreshCalendar();
}

function clearFilters() {
    document.getElementById('filter-coach').value = '';
    document.getElementById('filter-student').value = '';
    document.getElementById('filter-course').value = '';
    refreshCalendar();
}

// ==================== 重复选项 UI ====================

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.repeat-option').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.repeat-option').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const repeatType = this.dataset.repeat;
            document.getElementById('schedule-repeat-type').value = repeatType;
            document.getElementById('repeat-end-date-container').style.display =
                repeatType !== 'none' ? 'block' : 'none';
            // 每周重复时显示周几选择
            document.getElementById('repeat-days-container').style.display =
                repeatType === 'weekly' ? 'block' : 'none';
        });
    });
});

// ==================== 初始化 ====================

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
    // 确保模态框完全隐藏（处理CSS过渡可能导致的可见性问题）
    setTimeout(() => {
        if (!modal.classList.contains('active')) {
            modal.style.display = 'none';
        }
    }, 300);
}

async function init() {
    if (!await checkAuth()) return;

    await Promise.all([loadStudents(), loadCourses(), loadTemplates()]);
    loadCoaches();
    initCalendar();
    showScheduleList();
    initResizers();

    document.getElementById('student-form').addEventListener('submit', saveStudent);
    document.getElementById('course-form').addEventListener('submit', saveCourse);
    document.getElementById('template-form').addEventListener('submit', saveTemplate);
    document.getElementById('schedule-form').addEventListener('submit', saveSchedule);
    document.getElementById('coach-form').addEventListener('submit', saveCoach);
    document.getElementById('attendance-form').addEventListener('submit', submitAttendance);
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// 可调分隔条功能
function initResizers() {
    const detailResizer = document.getElementById('detail-resizer');
    const detailPanel = document.getElementById('detail-panel');

    if (!detailResizer) return;

    let isResizing = false;

    detailResizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        detailResizer.classList.add('active');
        document.body.style.cursor = 'col-resize';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const containerRect = document.querySelector('.container').getBoundingClientRect();
        const newWidth = containerRect.right - e.clientX;
        if (newWidth >= 250 && newWidth <= 600) {
            detailPanel.style.width = newWidth + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            detailResizer.classList.remove('active');
            document.body.style.cursor = '';
        }
    });

    // 触摸支持
    detailResizer.addEventListener('touchstart', (e) => {
        isResizing = true;
        detailResizer.classList.add('active');
        e.preventDefault();
    });

    document.addEventListener('touchmove', (e) => {
        if (!isResizing) return;
        const touch = e.touches[0];

        const containerRect = document.querySelector('.container').getBoundingClientRect();
        const newWidth = containerRect.right - touch.clientX;
        if (newWidth >= 250 && newWidth <= 600) {
            detailPanel.style.width = newWidth + 'px';
        }
    });

    document.addEventListener('touchend', () => {
        if (isResizing) {
            isResizing = false;
            detailResizer.classList.remove('active');
        }
    });
}

init();
