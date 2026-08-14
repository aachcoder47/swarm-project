# FrontierX - YC Demo Video Script
**Duration: 2-3 minutes**

---

## [0:00-0:15] Hook - The Problem

**Visual:** Dark warehouse setting, flickering lights, industrial equipment
**Audio:** Ambient industrial sounds, low tension music

**Narrator:**
"Industrial facilities are dangerous. When critical equipment fails, human inspectors risk their lives in hazardous environments. Generators overheat, valves leak, and components break—often in places no human should go."

**Visual:** Split screen showing:
- Worker in hazmat suit inspecting generator
- Thermal camera showing overheating equipment
- Statistics overlay: "2.8M workplace injuries annually in manufacturing"

---

## [0:15-0:30] The Solution

**Visual:** Fade to FrontierX logo, then to clean modern interface
**Audio:** Music shifts to upbeat, tech-forward

**Narrator:**
"Meet FrontierX. We're building the autonomous future of industrial inspection. Our AI-powered multi-robot system can navigate hazardous environments, identify problems, and execute repairs—without putting humans at risk."

**Visual:** 
- Animated diagram showing: Central AI Brain → Multiple Robots → Sensors → Dashboard
- Text overlay: "Autonomous. Intelligent. Safe."

---

## [0:30-1:00] Technical Architecture

**Visual:** Screen recording of the system in action
**Audio:** Keyboard typing sounds, system beeps

**Narrator:**
"At the core is our Central AI Brain—a ROS 2-based orchestration platform that coordinates multiple robots simultaneously. It uses natural language understanding to translate mission commands into executable skill plans."

**Visual:** 
- Dashboard showing command: "Find the generator and inspect it"
- AI generating step-by-step plan in real-time
- Robot registry showing 2 active robots (Scout UGV + Arm Manipulator)

**Narrator:**
"Our system supports heterogeneous robot fleets—UGVs for navigation, robotic arms for manipulation, drones for aerial inspection. Each robot is registered with its capabilities, and the AI automatically assigns the right robot to each task."

---

## [1:00-1:45] Live Demo

**Visual:** Split screen showing:
- Left: Gazebo simulation with Scout robot moving through warehouse
- Right: Dashboard with real-time telemetry and animated world map
- Bottom: Terminal showing ROS 2 topics and bridge status

**Narrator:**
"Watch as our Scout UGV autonomously navigates to a damaged generator. The system receives sensor data from LiDAR, RGB cameras, and thermal sensors—all processed in real-time through our ROS 2 bridge."

**Visual:** 
- Robot trail animation on dashboard map
- Robot status indicators changing from IDLE to MOVING to ACTIVE
- World objects appearing: generator (DAMAGED), charging dock, valves

**Narrator:**
"The dashboard provides complete situational awareness. You see robot positions, mission progress, and inspection findings—all in real-time. When the Scout identifies an overheating generator, it automatically dispatches the robotic arm to perform the repair."

**Visual:** 
- Plan execution showing steps completing with checkmarks
- Inspection report appearing with findings
- Robot returning to charging dock

---

## [1:45-2:15] Key Differentiators

**Visual:** Feature highlights with icons and text
**Audio:** Confident, energetic music

**Narrator:**
"What sets FrontierX apart:

**First**, our AI is deterministic and safe. We use rule-based planning with LLM fallback—no hallucinations, no unpredictable behavior.

**Second**, we're ROS 2 native. This means we integrate with existing robotics infrastructure and support any robot that speaks ROS.

**Third**, our system is hardware-agnostic. From $500 consumer drones to $100K industrial arms—we orchestrate them all.

 **Fourth**, real-time safety supervision. Our policy supervisor can E-stop the entire fleet in milliseconds if something goes wrong."

**Visual:** 
- Safety policy diagram showing watchdog timers
- E-stop button on dashboard
- Safety metrics panel

---

## [2:15-2:30] Market Opportunity

**Visual:** Market size graphics, industry logos
**Audio:** Professional, business-focused tone

**Narrator:**
"The industrial inspection market is $12B annually. Our initial focus is power plants, manufacturing facilities, and warehouses—environments where autonomous inspection can save lives and millions in downtime."

**Visual:** 
- Market size chart: "$12B Industrial Inspection Market"
- Customer logos: energy companies, manufacturers, logistics providers
- Traction placeholder: "Pilot programs with 3 Fortune 500 companies"

---

## [2:30-2:45] The Ask

**Visual:** Founders on camera or team photo
**Audio:** Warm, confident music

**Narrator:**
"We're the team to build this. Our founders have backgrounds in robotics engineering, AI research, and industrial automation. We've built working prototypes, integrated with real hardware, and deployed in simulation environments."

**Visual:** 
- Team photos
- GitHub commit graph showing active development
- Architecture diagram

**Narrator:**
"We're raising to scale our engineering team, deploy pilot programs with early customers, and expand our robot compatibility library. Join us in building the autonomous future of industrial inspection."

**Visual:** 
- FrontierX logo with tagline: "Autonomous Industrial Inspection"
- Contact information: founders@frontierx.ai
- Fade to black

---

## Production Notes

**Visual Style:**
- Clean, modern aesthetic
- Dark theme with neon green accents (matching dashboard)
- Screen recordings should be crisp, 1080p minimum
- Use split screens to show multiple system components simultaneously

**Audio:**
- Professional voiceover (calm, authoritative, tech-savvy)
- Background music: starts tense, shifts to upbeat tech, ends confident
- Sound effects: keyboard typing, system beeps, robot motors

**Screen Recordings Needed:**
1. Dashboard with animated world map
2. Gazebo simulation with robot movement
3. Command input and AI plan generation
4. ROS 2 terminal with topic monitoring
5. Safety E-stop demonstration
6. Multi-robot coordination (if available)

**B-Roll Footage:**
- Industrial warehouse (stock or filmed)
- Robots in action (simulation or real hardware)
- Team working on code
- Hardware components (LiDAR, cameras, robot arms)

**Text Overlays:**
- Keep minimal, use for emphasis only
- Font: Inter or Roboto, white on dark backgrounds
- Duration: 2-3 seconds per overlay

**Call to Action:**
- Display contact info for final 5 seconds
- Include website URL if live
- YC application reference if applicable
