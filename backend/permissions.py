"""账号角色、候选人阶段与操作权限（前后端共用的规则来源）

管理员固定拥有全部权限，不参与配置；HR / 技术面试官的操作权限
存在数据库 role_permissions 表中，可由管理员在「角色权限」里勾选调整。
"""

# 角色
ROLE_LABELS = {
    "admin": "管理员",
    "hr": "HR",
    "tech": "技术面试官",
}
ROLES = tuple(ROLE_LABELS)

# 候选人阶段（按看板顺序），owner 表示该阶段由谁负责推进
STATUSES = [
    {"key": "new", "label": "新简历", "owner": "hr", "color": "#7c8798", "tint": "#f1f4f9"},
    {"key": "screening", "label": "HR 初筛", "owner": "hr", "color": "#2456e6", "tint": "#eaf0ff"},
    {"key": "tech_review", "label": "待技术评估", "owner": "tech", "color": "#2f8aa8", "tint": "#e8f4f8"},
    {"key": "interview", "label": "面试中", "owner": "tech", "color": "#6c52d4", "tint": "#efecfd"},
    {"key": "tech_passed", "label": "面试通过待定 offer", "owner": "hr", "color": "#c2811f", "tint": "#fdf5e6"},
    {"key": "offered", "label": "已通过", "owner": "hr", "color": "#0f8a68", "tint": "#e6f6f0"},
    {"key": "rejected", "label": "已淘汰", "owner": "hr", "color": "#cc3d3d", "tint": "#fdeaea"},
]
STATUS_KEYS = tuple(s["key"] for s in STATUSES)
STATUS_LABELS = {s["key"]: s["label"] for s in STATUSES}

# 终态：进入后开始 7 天倒计时，到期自动删除
FINAL_STATUSES = ("offered", "rejected")

# 默认阶段流转矩阵（仅作默认配置与文案参考，实际以授权为准）
TRANSITIONS = {
    "new": {
        "screening": ("hr", "admin"),
        "rejected": ("hr", "admin"),
    },
    "screening": {
        "tech_review": ("hr", "admin"),
        "rejected": ("hr", "admin"),
    },
    "tech_review": {
        # HR 可撤回推送，技术部决定是否约面
        "screening": ("hr", "admin"),
        "interview": ("tech", "admin"),
        "rejected": ("tech", "admin"),
    },
    "interview": {
        "tech_passed": ("tech", "admin"),
        "rejected": ("tech", "admin"),
    },
    "tech_passed": {
        "offered": ("hr", "admin"),
        "rejected": ("hr", "admin"),
    },
    "offered": {},
    "rejected": {},
}

# 技术部默认可见的阶段：HR 已推送、且尚未有终局结论
TECH_VISIBLE_STATUSES = ("tech_review", "interview", "tech_passed")


# ---------------------------------------------------------------------------
# 可配置的操作权限
# ---------------------------------------------------------------------------
PERMISSION_GROUPS = [
    {
        "title": "候选人流程",
        "items": [
            {
                "key": "candidate.upload",
                "label": "上传 / 导入简历",
                "hint": "包含邮箱同步与附件解析入库",
            },
            {
                "key": "ai.chat",
                "label": "AI 对话筛选",
                "hint": "用自然语言检索候选人库，不受可见范围限制",
            },
            {
                "key": "stage.screen",
                "label": "简历初筛",
                "hint": "新简历 → HR 初筛",
            },
            {
                "key": "stage.push_tech",
                "label": "推送技术部",
                "hint": "HR 初筛 → 待技术评估，也包含从技术评估撤回",
            },
            {
                "key": "stage.schedule",
                "label": "约面试",
                "hint": "待技术评估 → 面试中",
            },
            {
                "key": "stage.interview_result",
                "label": "判定面试结果",
                "hint": "面试中 → 面试通过待定 offer",
            },
            {
                "key": "stage.offer",
                "label": "发 offer",
                "hint": "面试通过待定 offer → 已通过",
            },
            {
                "key": "stage.reject",
                "label": "淘汰候选人",
                "hint": "开启后可在任何未出结果的环节淘汰",
            },
        ],
    },
    {
        "title": "数据与档案",
        "items": [
            {
                "key": "candidate.view_all",
                "label": "查看全部候选人",
                "hint": "关闭后仅能看到已推送、尚未定论的候选人",
            },
            {
                "key": "candidate.edit",
                "label": "编辑候选人资料",
                "hint": "修改姓名、岗位、联系方式等档案字段",
            },
            {
                "key": "candidate.delete",
                "label": "删除候选人档案",
                "hint": "删除后不可恢复",
            },
            {
                "key": "interview.manage",
                "label": "安排面试与记录反馈",
                "hint": "维护面试时间、形式、面试官与反馈内容",
            },
        ],
    },
    {
        "title": "系统管理",
        "items": [
            {
                "key": "email.config",
                "label": "邮箱通知配置",
                "hint": "配置收件邮箱、同步规则与测试连接",
            },
            {
                "key": "users.manage",
                "label": "账号与权限管理",
                "hint": "仅管理员，不可授予其他角色",
            },
        ],
    },
]

ALL_PERMISSION_KEYS = tuple(item["key"] for g in PERMISSION_GROUPS for item in g["items"])
PERMISSION_LABELS = {item["key"]: item["label"] for g in PERMISSION_GROUPS for item in g["items"]}

# 不可授予非管理员的权限
ADMIN_ONLY_PERMISSIONS = ("users.manage",)

# 默认授权（管理员固定全部）
DEFAULT_ROLE_PERMISSIONS = {
    "hr": [
        "candidate.upload",
        "ai.chat",
        "stage.screen",
        "stage.push_tech",
        "stage.offer",
        "stage.reject",
        "candidate.view_all",
        "candidate.edit",
        "candidate.delete",
    ],
    "tech": [
        "stage.schedule",
        "stage.interview_result",
        "stage.reject",
        "interview.manage",
    ],
}

# 阶段流转需要的权限
TRANSITION_PERMISSIONS = {
    ("new", "screening"): "stage.screen",
    ("screening", "tech_review"): "stage.push_tech",
    ("tech_review", "screening"): "stage.push_tech",
    ("tech_review", "interview"): "stage.schedule",
    ("interview", "tech_passed"): "stage.interview_result",
    ("tech_passed", "offered"): "stage.offer",
}


def all_permissions():
    """管理员拥有的全部权限"""
    return set(ALL_PERMISSION_KEYS)


def default_permissions(role):
    """角色未做配置时的默认权限"""
    if role == "admin":
        return all_permissions()
    return set(DEFAULT_ROLE_PERMISSIONS.get(role, []))


def has_permission(role, key, perms=None):
    """判断角色是否拥有某项操作权限；perms 为 {role: set(keys)} 配置"""
    if role == "admin":
        return True
    allowed = perms.get(role) if perms else None
    if allowed is None:
        allowed = default_permissions(role)
    return key in allowed


def can_view_all_candidates(role, perms=None):
    return has_permission(role, "candidate.view_all", perms)


def transition_permission(from_status, to_status):
    """阶段流转对应的权限 key"""
    if to_status == "rejected":
        return "stage.reject"
    return TRANSITION_PERMISSIONS.get((from_status, to_status))


def can_transition(role, from_status, to_status, perms=None):
    """判断角色能否把候选人从 from_status 推到 to_status"""
    if role == "admin":
        return to_status in STATUS_KEYS and from_status != to_status
    if from_status not in STATUS_KEYS or to_status not in STATUS_KEYS:
        return False
    if from_status == to_status:
        return False
    key = transition_permission(from_status, to_status)
    if not key:
        return False
    if to_status == "rejected" and from_status in FINAL_STATUSES:
        return False
    return has_permission(role, key, perms)


def allowed_targets(role, from_status, perms=None):
    """某角色在 from_status 阶段可以推进到的目标阶段"""
    return [
        k
        for k in STATUS_KEYS
        if k != from_status and can_transition(role, from_status, k, perms)
    ]


def transition_error(role, from_status, to_status):
    """生成权限不足时的中文提示"""
    target_roles = TRANSITIONS.get(from_status, {}).get(to_status, ())
    if not target_roles and to_status != "rejected":
        return (
            f"「{STATUS_LABELS.get(from_status, from_status)}」"
            f"不能直接流转到「{STATUS_LABELS.get(to_status, to_status)}」"
        )
    names = "、".join(ROLE_LABELS.get(r, r) for r in target_roles if r != "admin")
    hint = f"（默认由{names}负责）" if names else ""
    return (
        f"当前角色（{ROLE_LABELS.get(role, role)}）没有"
        f"「{STATUS_LABELS.get(to_status, to_status)}」环节的操作权限{hint}，"
        "请联系管理员在「角色权限」中开通"
    )
