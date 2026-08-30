export class LearningService {
  constructor() {
    this.name = "learning_service";
  }

  async generateLearningPlan(userId, targetRole, targetSkills, currentSkills, skillGaps, weeklyHours = 10, learningStyle = "mixed", budget = 0, targetDate = null) {
    return {
      id: `plan_${Date.now()}`,
      userId,
      targetRole,
      targetSkills,
      currentSkills,
      skillGaps,
      phases: [],
      totalEstimatedWeeks: 0,
      weeklyTimeCommitmentHours: weeklyHours,
      startDate: new Date(),
      targetCompletionDate: targetDate,
      learningStyle,
      budget,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
  }

  getResourceRecommendations(skill, difficulty = null, budget = 0) {
    const resources = [
      {
        title: `${skill} Fundamentals`,
        resourceType: "course",
        provider: "Coursera",
        url: `https://coursera.org/learn/${skill.toLowerCase()}`,
        difficulty: "beginner",
        estimatedHours: 20,
        cost: 0,
        rating: 4.8,
        skillsCovered: [skill],
        prerequisites: [],
        certification: true,
      },
      {
        title: `Advanced ${skill}`,
        resourceType: "course",
        provider: "Udemy",
        url: `https://udemy.com/course/advanced-${skill.toLowerCase()}`,
        difficulty: "advanced",
        estimatedHours: 40,
        cost: 50,
        rating: 4.7,
        skillsCovered: [skill],
        prerequisites: [],
        certification: true,
      },
    ];

    let filtered = resources;
    if (difficulty) {
      filtered = filtered.filter(r => r.difficulty === difficulty);
    }
    if (budget === 0) {
      filtered = filtered.filter(r => r.cost === 0);
    }
    return filtered;
  }

  getSkillPrerequisites(skill) {
    const prereqMap = {
      "React": ["JavaScript", "HTML", "CSS"],
      "Node.js": ["JavaScript", "Async Programming"],
      "Django": ["Python", "SQL", "HTTP Basics"],
      "FastAPI": ["Python", "Async Programming", "REST APIs"],
      "Kubernetes": ["Docker", "Linux", "Networking", "YAML"],
      "Machine Learning": ["Python", "Statistics", "Linear Algebra", "Calculus"],
      "Deep Learning": ["Machine Learning", "Python", "Linear Algebra"],
      "AWS": ["Linux", "Networking", "Security Basics"],
      "Terraform": ["AWS/GCP/Azure", "Infrastructure Concepts"],
      "CI/CD": ["Git", "Linux", "Scripting", "Docker"],
      "GraphQL": ["REST APIs", "JavaScript/TypeScript", "Database Basics"],
      "TypeScript": ["JavaScript", "Static Typing Concepts"],
      "Next.js": ["React", "TypeScript", "Node.js"],
      "PostgreSQL": ["SQL", "Database Design", "Relational Theory"],
      "Redis": ["Caching Concepts", "Data Structures", "Linux"],
      "Kafka": ["Distributed Systems", "Messaging Patterns", "Java/Go"],
    };
    return prereqMap.get(skill, []);
  }
}

const learningService = new LearningService();
export default learningService;

export const LearningStyle = {
  VISUAL: "visual",
  READING: "reading",
  HANDS_ON: "hands_on",
  AUDIO: "audio",
  MIXED: "mixed",
};

export const DifficultyLevel = {
  BEGINNER: "beginner",
  INTERMEDIATE: "intermediate",
  ADVANCED: "advanced",
  EXPERT: "expert",
};

export const ResourceType = {
  COURSE: "course",
  BOOK: "book",
  ARTICLE: "article",
  VIDEO: "video",
  CERTIFICATION: "certification",
  PROJECT: "project",
  PRACTICE: "practice",
  WORKSHOP: "workshop",
  BOOTCAMP: "bootcamp",
  MENTORSHIP: "mentorship",
};