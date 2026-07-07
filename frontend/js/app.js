/**
 * AI 智能简历分析系统 - 前端交互逻辑
 */

// ===== 配置 =====
// 后端 API 地址（部署时修改为实际地址）
const API_BASE = 'http://localhost:8000/api/v1';

// ===== DOM 元素 =====
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadBtn = document.getElementById('upload-btn');
const uploadInfo = document.getElementById('upload-info');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');
const progressBar = document.getElementById('progress-bar');
const uploadError = document.getElementById('upload-error');

const resultSection = document.getElementById('result-section');
const matchSection = document.getElementById('match-section');
const matchBtn = document.getElementById('match-btn');
const jdInput = document.getElementById('jd-input');
const matchSpinner = document.getElementById('match-spinner');
const matchError = document.getElementById('match-error');
const matchResultSection = document.getElementById('match-result-section');

// 当前简历 ID
let currentResumeId = null;

// ===== 工具函数 =====
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
}

function hideError(element) {
    element.style.display = 'none';
    element.textContent = '';
}

function fadeIn(element) {
    element.style.opacity = '0';
    element.style.display = '';
    requestAnimationFrame(() => {
        element.style.transition = 'opacity .3s ease';
        element.style.opacity = '1';
    });
}

// ===== 文件上传 =====
uploadBtn.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('click', () => fileInput.click());

// 拖拽上传
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (file) handleFile(file);
});

function handleFile(file) {
    // 验证文件类型
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError(uploadError, '⚠️ 仅支持 PDF 格式的文件');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showError(uploadError, '⚠️ 文件大小不能超过 10MB');
        return;
    }

    hideError(uploadError);

    // 显示文件信息
    fileName.textContent = '📎 ' + file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadInfo.style.display = 'flex';

    // 上传并解析
    uploadAndParse(file);
}

async function uploadAndParse(file) {
    // 显示进度条
    progressBar.style.display = '';
    uploadError.style.display = 'none';

    // 隐藏之前的结果
    resultSection.style.display = 'none';
    matchSection.style.display = 'none';
    matchResultSection.style.display = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/resume/upload`, {
            method: 'POST',
            body: formData,
        });

        progressBar.style.display = 'none';

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '上传失败');
        }

        const data = await response.json();
        currentResumeId = data.id;
        displayResumeResult(data);

    } catch (error) {
        progressBar.style.display = 'none';
        showError(uploadError, '❌ ' + error.message);
    }
}

// ===== 展示解析结果 =====
function displayResumeResult(data) {
    // 基本信息
    document.getElementById('res-name').textContent = data.basic_info?.name || '未识别';
    document.getElementById('res-phone').textContent = data.basic_info?.phone || '未识别';
    document.getElementById('res-email').textContent = data.basic_info?.email || '未识别';
    document.getElementById('res-address').textContent = data.basic_info?.address || '未识别';

    // 求职信息
    document.getElementById('res-intent').textContent = data.job_intent || '未识别';
    document.getElementById('res-salary').textContent = data.expected_salary || '未识别';
    document.getElementById('res-years').textContent = data.work_years || '未识别';
    document.getElementById('res-edu').textContent = data.education || '未识别';

    // 技能
    const skillsGroup = document.getElementById('skills-group');
    const skillsList = document.getElementById('res-skills');
    if (data.skills && data.skills.length > 0) {
        skillsGroup.style.display = '';
        skillsList.innerHTML = data.skills
            .map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`)
            .join('');
    } else {
        skillsGroup.style.display = 'none';
    }

    // 项目经历
    const projectsGroup = document.getElementById('projects-group');
    const projectsList = document.getElementById('res-projects');
    if (data.projects && data.projects.length > 0) {
        projectsGroup.style.display = '';
        projectsList.innerHTML = data.projects
            .map(p => `<li>${escapeHtml(p)}</li>`)
            .join('');
    } else {
        projectsGroup.style.display = 'none';
    }

    // 显示结果区域
    fadeIn(resultSection);

    // 显示匹配区域
    fadeIn(matchSection);
    matchBtn.disabled = false;
}

// ===== 岗位匹配 =====
jdInput.addEventListener('input', () => {
    matchBtn.disabled = !jdInput.value.trim();
});

matchBtn.addEventListener('click', () => {
    const jd = jdInput.value.trim();
    if (!jd || !currentResumeId) return;
    performMatch(jd);
});

async function performMatch(jobDescription) {
    matchBtn.style.display = 'none';
    matchSpinner.style.display = '';
    matchError.style.display = 'none';
    matchResultSection.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/resume/${currentResumeId}/match`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_description: jobDescription }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || '匹配分析失败');
        }

        const data = await response.json();
        displayMatchResult(data);

    } catch (error) {
        showError(matchError, '❌ ' + error.message);
    } finally {
        matchSpinner.style.display = 'none';
        matchBtn.style.display = '';
    }
}

// ===== 展示匹配结果 =====
function displayMatchResult(data) {
    // 总分
    const score = Math.round(data.match_score);
    document.getElementById('score-value').textContent = score;

    // 分数圆环颜色
    const circle = document.getElementById('score-circle');
    circle.style.background = score >= 80
        ? 'linear-gradient(135deg, #10b981, #059669)'
        : score >= 60
            ? 'linear-gradient(135deg, #f59e0b, #d97706)'
            : 'linear-gradient(135deg, #ef4444, #dc2626)';

    // 分项得分
    const skill = data.details?.skill_match || 0;
    const exp = data.details?.experience_relevance || 0;
    const edu = data.details?.education_match || 0;

    document.getElementById('bar-skill').style.width = skill + '%';
    document.getElementById('val-skill').textContent = Math.round(skill) + '%';

    document.getElementById('bar-exp').style.width = exp + '%';
    document.getElementById('val-exp').textContent = Math.round(exp) + '%';

    document.getElementById('bar-edu').style.width = edu + '%';
    document.getElementById('val-edu').textContent = Math.round(edu) + '%';

    // 关键词
    const kwGroup = document.getElementById('keywords-group');
    const kwList = document.getElementById('match-keywords');
    if (data.keywords && data.keywords.length > 0) {
        kwGroup.style.display = '';
        kwList.innerHTML = data.keywords
            .map(k => `<span class="skill-tag">${escapeHtml(k)}</span>`)
            .join('');
    } else {
        kwGroup.style.display = 'none';
    }

    // AI 分析
    const analysisGroup = document.getElementById('analysis-group');
    if (data.analysis) {
        analysisGroup.style.display = '';
        document.getElementById('match-analysis').textContent = data.analysis;
    } else {
        analysisGroup.style.display = 'none';
    }

    // 显示结果
    fadeIn(matchResultSection);
    matchResultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===== 工具函数 =====
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
