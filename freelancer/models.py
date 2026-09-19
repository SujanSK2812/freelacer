from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Project(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    budget = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')  # ✅ ADD THIS
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# models.py

from django.db import models
from django.contrib.auth import get_user_model

from freelancer_portal.upload_utils import SafeImageField, freelancer_profile_path

User = get_user_model()

class FreelancerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # BASIC INFO
    profile_picture = SafeImageField(upload_to=freelancer_profile_path, blank=True, null=True)
    title = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)

    # PROFESSIONAL DETAILS
    experience_level = models.CharField(max_length=50, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ], blank=True)

    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # SKILLS (like Upwork tags)
    skills = models.TextField(blank=True, help_text="Comma separated skills")

    def get_skills_list(self):
        if not self.skills:
            return []
        return [skill.strip() for skill in self.skills.split(',') if skill.strip()]

    # EDUCATION
    education = models.TextField(blank=True)

    # EXPERIENCE
    work_experience = models.TextField(blank=True)

    @property
    def work_experience_html(self):
        import re
        from django.utils.html import escape
        if not self.work_experience:
            return ""
        
        # Escape HTML first for safety
        text = escape(self.work_experience)
        
        # ### Job Title -> <h3 class="exp-job-title">Job Title</h3>
        text = re.sub(r'^###\s+(.*)$', r'<h3 class="exp-job-title">\1</h3>', text, flags=re.MULTILINE)
        
        # **Date** on its own line -> <div class="exp-date">\1</div>
        text = re.sub(r'^\*\*(.*?)\*\*$', r'<div class="exp-date">\1</div>', text, flags=re.MULTILINE)
        
        # Remaining **bold** -> <strong>bold</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # Convert newlines to <br> or wrap in <p> (simple linebreaksbr)
        text = text.replace('\r\n', '\n')
        # We can split by double newlines for paragraphs, but simple <br> is often enough
        # Actually, let's wrap non-header/non-date blocks in <p class="exp-desc">
        
        blocks = text.split('\n\n')
        html_blocks = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if block.startswith('<h3') or block.startswith('<div class="exp-date"'):
                # For blocks that have headers, we don't wrap the header, but if they have text after, we should.
                # Since re.MULTILINE matched, a block might contain <h3>\n<div...>\nText
                # Let's just do line by line.
                pass
            
        # A simpler approach: line by line
        lines = text.split('\n')
        out_lines = []
        in_p = False
        for line in lines:
            line = line.strip()
            if not line:
                if in_p:
                    out_lines.append('</p>')
                    in_p = False
                continue
            
            if line.startswith('<h') or line.startswith('<div'):
                if in_p:
                    out_lines.append('</p>')
                    in_p = False
                out_lines.append(line)
            else:
                if not in_p:
                    out_lines.append('<p class="exp-desc">')
                    in_p = True
                out_lines.append(line + '<br>')
                
        if in_p:
            out_lines.append('</p>')
            
        return '\n'.join(out_lines).replace('<br></p>', '</p>')

    # PORTFOLIO
    portfolio_link = models.URLField(blank=True)
    github_link = models.URLField(blank=True)

    # SOCIAL
    linkedin = models.URLField(blank=True)

    # LOCATION
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # AVAILABILITY
    is_available = models.BooleanField(default=True)

    # COMPLETION FLAGS (for skip logic)
    is_basic_completed = models.BooleanField(default=False)
    is_professional_completed = models.BooleanField(default=False)
    is_portfolio_completed = models.BooleanField(default=False)

    profile_views = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    @property
    def profile_completeness(self):
        fields_to_check = [
            self.profile_picture,
            self.title,
            self.bio,
            self.experience_level,
            self.hourly_rate,
            self.skills,
            self.education,
            self.work_experience,
            self.portfolio_link,
            self.github_link,
            self.linkedin,
            self.country,
            self.city
        ]
        
        filled_count = 0
        total_fields = len(fields_to_check)
        
        for field in fields_to_check:
            if field is not None:
                if isinstance(field, str):
                    if field.strip() != "":
                        filled_count += 1
                else:
                    filled_count += 1
                    
        return int((filled_count / total_fields) * 100)