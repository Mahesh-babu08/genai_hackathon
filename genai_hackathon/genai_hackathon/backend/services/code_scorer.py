import re
from typing import Dict, Any, List

class CodeQualityScorer:
    """
    Calculates code quality scores based on static analysis heuristics
    and AI review results.
    """
    
    def calculate_scores(self, review_result: Dict[str, Any], code: str, language: str) -> Dict[str, Any]:
        """
        Calculate quality scores (0-100) for different categories.
        """
        counts = review_result.get("counts", {})
        critical_issues = counts.get("critical", 0)
        high_issues = counts.get("high", 0)
        medium_issues = counts.get("medium", 0)
        low_issues = counts.get("low", 0)
        
        # 1. Security Score (Starts at 100)
        # Penalties: Critical=25, High=15, Medium=5
        security_penalty = (critical_issues * 25) + (high_issues * 15) + (medium_issues * 5)
        
        # Additional keyword check
        security_keywords = ["password", "secret", "key", "token", "auth", "eval", "exec", "os.system"]
        security_matches = self._count_keywords(code, security_keywords)
        security_penalty += (security_matches * 2)
        
        security_score = max(0, 100 - security_penalty)
        
        # 2. Performance Score (Starts at 100)
        # Penalties: High=15, Medium=5
        perf_penalty = (high_issues * 15) + (medium_issues * 5)
        
        # Complexity penalty
        complexity_est = self._estimate_complexity(code)
        if complexity_est > 20: perf_penalty += 20
        elif complexity_est > 10: perf_penalty += 10
        
        performance_score = max(0, 100 - perf_penalty)
        
        # 3. Maintainability Score (Starts at 100)
        # Based on code length, function count, and issues
        maint_penalty = (critical_issues * 10) + (high_issues * 5) + (medium_issues * 2)
        
        # Length penalty (arbitrary thresholds)
        loc = len(code.split('\n'))
        if loc > 500: maint_penalty += 20
        elif loc > 200: maint_penalty += 10
        
        maintainability_score = max(0, 100 - maint_penalty)
        
        # 4. Readability Score (Starts at 100)
        read_penalty = (medium_issues * 3) + (low_issues * 1)
        
        # Comment ratio check
        lines = code.split('\n')
        comment_lines = len([l for l in lines if l.strip().startswith(('#', '//', '/*', '*'))])
        if loc > 10 and (comment_lines / loc) < 0.05:
            read_penalty += 15 # Low comment ratio
            
        readability_score = max(0, 100 - read_penalty)
        
        # Overall Score (Weighted)
        overall_score = (
            (security_score * 0.35) +
            (performance_score * 0.25) +
            (maintainability_score * 0.20) +
            (readability_score * 0.20)
        )
        
        return {
            "overall": round(overall_score),
            "categories": {
                "security": security_score,
                "performance": performance_score,
                "maintainability": maintainability_score,
                "readability": readability_score
            },
            "grade": self._get_grade(overall_score),
            "metrics": {
                "loc": loc,
                "complexity": complexity_est,
                "issues_count": critical_issues + high_issues + medium_issues + low_issues
            }
        }
    
    def _count_keywords(self, code: str, keywords: List[str]) -> int:
        count = 0
        code_lower = code.lower()
        for kw in keywords:
            count += code_lower.count(kw)
        return count
    
    def _estimate_complexity(self, code: str) -> int:
        # Very rough estimation based on indentation and keywords
        complexity = 0
        keywords = ["if", "for", "while", "except", "with", "case", "def", "class"]
        
        for line in code.split('\n'):
            line = line.strip()
            if any(line.startswith(kw) for kw in keywords):
                complexity += 1
                
        return complexity
    
    def _get_grade(self, score: float) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"

code_scorer = CodeQualityScorer()
