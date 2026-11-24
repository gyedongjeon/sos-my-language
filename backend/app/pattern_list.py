"""The built-in sentence patterns, by CEFR level.

There is no official level for a pattern; each one is placed where the grammar it needs is
usually taught (the English Grammar Profile was the reference). An id is kept for good: saved
progress points at it.
"""

from dataclasses import dataclass

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


@dataclass(frozen=True)
class Pattern:
    id: str
    level: str
    # The pattern as a formula, what it is used for, and one sentence that shows it.
    pattern: str
    use: str
    example: str


def _level(level: str, *rows: tuple[str, str, str, str]) -> list[Pattern]:
    return [Pattern(id, level, pattern, use, example) for id, pattern, use, example in rows]


PATTERNS: list[Pattern] = [
    *_level(
        "A1",
        ("id-like", "I'd like + noun / to + verb", "Asking for something politely", "I'd like a cup of coffee, please."),
        ("there-is", "There is / There are …", "Saying what is somewhere", "There are two parks near my house."),
        ("can", "I can / I can't + verb", "Saying what you are able to do", "I can swim, but I can't dive."),
        ("do-you-have", "Do you have …?", "Asking whether someone has something", "Do you have a pen?"),
        ("going-to", "I'm going to + verb", "Saying what you plan to do", "I'm going to visit my parents tomorrow."),
        ("like-ing", "I like / don't like + -ing", "Saying what you enjoy doing", "I like cooking, but I don't like washing the dishes."),
        ("can-i", "Can I + verb …?", "Asking if you may do something", "Can I sit here?"),
        ("how-much-many", "How much / How many …?", "Asking about an amount or a number", "How many people are coming?"),
        ("want-to", "I want to + verb", "Saying what you wish to do", "I want to learn English."),
        ("lets", "Let's + verb", "Suggesting something to do together", "Let's meet at six."),
        ("present-continuous", "I'm + -ing", "Saying what is happening now", "I'm waiting for the bus."),
        ("simple-past", "I + past verb", "Saying what happened at a finished time", "I watched a movie last night."),
        ("do-you", "Do you + verb …? / Does she + verb …?", "Asking about habits and facts", "Do you live near here?"),
        ("wh-questions", "What time / When / Where + do / does …?", "Asking for a time or a place", "What time does the store open?"),
        ("is-there", "Is there / Are there …?", "Asking whether something exists nearby", "Is there a bank near here?"),
        ("frequency", "always / usually / sometimes / never + verb", "Saying how often you do something", "I usually get up at seven."),
        ("need-to", "I need to + verb", "Saying what is necessary for you", "I need to buy some milk."),
        ("imperative", "Please + verb / Don't + verb", "Asking or telling someone to do something", "Please don't close the window."),
        ("i-think", "I think (that) …", "Giving a simple opinion", "I think it's a good idea."),
        ("was-were", "I was / We were …", "Saying where or how you were", "I was at home yesterday."),
    ),
    *_level(
        "A2",
        ("have-to", "have to / don't have to + verb", "Saying what is or is not necessary", "I have to get up early tomorrow."),
        ("past-continuous", "was / were + -ing + when + past", "Saying what was going on when something happened", "I was cooking when you called."),
        ("comparative", "-er than / more … than", "Comparing two things", "This bag is cheaper than that one."),
        ("superlative", "the -est / the most …", "Saying which one stands out from all", "It's the best restaurant in town."),
        ("have-you-ever", "Have you ever + past participle …?", "Asking about someone's experience", "Have you ever been to Japan?"),
        ("should", "should / shouldn't + verb", "Giving advice", "You should see a doctor."),
        ("first-conditional", "If + present, … will + verb", "Saying what will happen if something does", "If it rains, I'll stay home."),
        ("too-enough", "too + adjective + to / adjective + enough + to", "Saying why something is not possible, or is", "It's too cold to swim."),
        ("so-result", "…, so …", "Giving the result of something", "I was tired, so I went to bed early."),
        ("would-you-like", "Would you like + noun / to + verb …?", "Offering or inviting", "Would you like to join us?"),
        ("already-yet", "have just / already + past participle; haven't … yet", "Saying what is done or not done by now", "I haven't finished my homework yet."),
        ("will", "I'll + verb", "Deciding on the spot, offering, or promising", "I'll call you later."),
        ("could-you", "Could you + verb …?", "Asking someone politely to do something", "Could you help me with this?"),
        ("when-past", "When I was …, I + past verb", "Talking about a time in your past", "When I was a child, I lived by the sea."),
        ("want-someone-to", "want / ask / tell + someone + to + verb", "Saying what you wish another person to do", "I want you to come with me."),
        ("enjoy-ing", "enjoy / finish / stop + -ing", "Using a verb after these verbs", "I enjoy walking in the morning."),
        ("interested-in", "be good at / interested in + -ing", "Talking about skills and interests", "I'm interested in learning Spanish."),
        ("it-takes", "It takes + time + to + verb", "Saying how long something needs", "It takes twenty minutes to get there."),
        ("arranged-future", "I'm + -ing + future time", "Talking about something already arranged", "I'm meeting a friend tonight."),
        ("why-dont-we", "Why don't we + verb …? / How about + -ing …?", "Making a suggestion", "Why don't we take a taxi?"),
    ),
    *_level(
        "B1",
        ("present-perfect-continuous", "have been + -ing + for / since", "Saying how long something has been going on", "I've been learning English for three years."),
        ("used-to", "used to + verb", "Talking about a past habit or state that is over", "I used to play the piano."),
        ("second-conditional", "If + past, … would + verb", "Imagining something unreal now", "If I had more time, I would travel more."),
        ("passive", "be + past participle", "Saying what happens to something", "The bridge was built in 1990."),
        ("looking-forward", "I'm looking forward to + -ing", "Saying you are pleased about something coming", "I'm looking forward to seeing you."),
        ("reported-speech", "He said (that) + past", "Passing on what someone said", "She said she was busy."),
        ("relative-clause", "noun + who / which / that + …", "Saying which person or thing you mean", "The man who lives next door is a doctor."),
        ("might", "might / may + verb", "Saying something is possible", "I might be late tonight."),
        ("although", "Although / Even though …, …", "Setting one fact against another", "Although it was raining, we went out."),
        ("so-that-result", "so + adjective + that … / such + noun + that …", "Giving a strong reason for a result", "It was so hot that we stayed inside."),
        ("for-since", "have + past participle + for / since", "Saying how long a state has lasted", "I've lived here since 2020."),
        ("unless", "Unless + present, …", "Saying what happens if something does not", "Unless we hurry, we'll miss the train."),
        ("as-as", "as + adjective + as / not as … as", "Saying two things are, or are not, equal", "This one isn't as expensive as that one."),
        ("indirect-question", "Do you know / Could you tell me + question word + subject + verb", "Asking a question politely", "Could you tell me where the station is?"),
        ("past-perfect", "had + past participle", "Saying what had happened before another past event", "The movie had already started when we arrived."),
        ("would-rather", "I'd rather + verb (+ than + verb)", "Saying what you prefer to do", "I'd rather stay home than go out tonight."),
        ("purpose", "to / in order to + verb; so that + subject + can / could", "Saying why you do something", "I saved money so that I could travel."),
        ("able-to", "be able to / manage to + verb", "Saying you could or could not do something", "I wasn't able to sleep last night."),
        ("supposed-to", "be supposed to + verb", "Saying what is expected or arranged", "I'm supposed to be at work by nine."),
        ("question-tag", "…, isn't it? / …, don't you?", "Checking that someone agrees", "It's cold today, isn't it?"),
    ),
    *_level(
        "B2",
        ("should-have", "should have + past participle", "Regretting or criticising something in the past", "I should have left earlier."),
        ("third-conditional", "If + past perfect, … would have + past participle", "Imagining a different past", "If I had known, I would have told you."),
        ("wish", "I wish + past / past perfect", "Wishing things were, or had been, different", "I wish I had more free time."),
        ("have-something-done", "have / get + something + past participle", "Saying someone does a job for you", "I had my hair cut yesterday."),
        ("be-used-to", "be / get used to + -ing", "Saying something is, or is becoming, normal for you", "I'm getting used to working from home."),
        ("must-have", "must have / can't have + past participle", "Being sure about something in the past", "She must have forgotten about the meeting."),
        ("worth-ing", "It's worth + -ing / There's no point in + -ing", "Saying whether something deserves the effort", "It's worth visiting the old town."),
        ("the-more", "The more …, the more …", "Saying two things change together", "The more you practise, the better you get."),
        ("future-perfect", "By the time …, … will have + past participle", "Saying what will be finished by a future moment", "By the time you arrive, I'll have finished."),
        ("not-only", "not only … but also …", "Adding a second, stronger point", "She not only sings but also writes her own songs."),
        ("could-have", "could have / might have + past participle", "Saying what was possible but did not happen", "You could have told me."),
        ("if-only", "If only + past / past perfect", "Expressing a strong wish or regret", "If only I had listened to you."),
        ("despite", "Despite / In spite of + -ing / noun", "Setting a fact against what you would expect", "Despite being tired, she kept working."),
        ("no-matter", "No matter + what / how / where …", "Saying something makes no difference", "No matter what happens, I'll support you."),
        ("as-long-as", "as long as / provided (that) …", "Giving a condition", "You can borrow it as long as you bring it back."),
        ("likely-to", "be likely to / be about to + verb", "Saying something is probable or just ahead", "Prices are likely to rise next year."),
        ("whether-or-not", "whether … or not", "Talking about two possibilities", "I don't know whether he's coming or not."),
        ("which-comment", "…, which + verb", "Commenting on everything you just said", "He was late again, which annoyed everyone."),
        ("modal-passive", "modal / need to + be + past participle", "Saying what must or should happen to something", "The report needs to be finished by Friday."),
        ("would-habit", "would + verb (past habit)", "Describing something you did repeatedly in the past", "When I was young, we would go fishing every summer."),
    ),
    *_level(
        "C1",
        ("never-have-i", "Never / Rarely / Seldom + auxiliary + subject", "Stressing how unusual something is", "Never have I seen such a mess."),
        ("not-only-inversion", "Not only + auxiliary + subject …, but … also …", "Stressing a second point", "Not only did he apologise, but he also paid for the damage."),
        ("had-i", "Had + subject + past participle, … would have …", "Imagining a different past, formally", "Had I known, I would have come earlier."),
        ("mixed-conditional", "If + past perfect, … would + verb (now)", "Linking a different past to the present", "If I had taken that job, I would be living in London now."),
        ("what-cleft", "What + clause + is / was …", "Putting the weight on one part of the sentence", "What I need is a long holiday."),
        ("it-cleft", "It is / was … that / who …", "Pointing at the one person or thing you mean", "It was my sister who told me."),
        ("its-time", "It's (high) time + subject + past", "Saying something should happen now", "It's time we left."),
        ("participle-clause", "Having + past participle, … / -ing …, …", "Joining two actions in one sentence", "Having finished the report, she went home."),
        ("said-to", "be said / believed / thought to + verb", "Reporting what people in general say", "He is said to be the best in his field."),
        ("rather-you", "I'd rather + subject + past", "Saying what you would like someone else to do", "I'd rather you didn't tell anyone."),
        ("no-sooner", "No sooner had + subject + past participle than …", "Saying one thing followed another at once", "No sooner had I left than it started to rain."),
        ("only-after", "Only when / Only after … + auxiliary + subject", "Stressing the moment something happened", "Only after the meeting did I realise my mistake."),
    ),
    *_level(
        "C2",
        ("were-to", "Were + subject + to + verb, … would …", "Imagining an unlikely future, formally", "Were the company to fail, thousands would lose their jobs."),
        ("subjunctive", "insist / suggest / demand + that + subject + base verb", "Saying what someone requires, formally", "They insisted that he be present."),
        ("hardly-when", "Hardly / Scarcely had + subject + past participle when …", "Saying one thing came right after another", "Hardly had we sat down when the phone rang."),
        ("adjective-as", "Adjective + as / though + subject + verb, …", "Setting a fact aside, with emphasis", "Hard as she tried, she couldn't open the door."),
        ("should-you", "Should + subject + verb, …", "Giving a condition, formally", "Should you need any help, please let me know."),
        ("so-inversion", "So + adjective + be + subject + that …", "Stressing a cause and its result", "So great was the demand that the shop sold out in an hour."),
        ("little-did", "Little did + subject + know / realise …", "Saying someone had no idea of what was coming", "Little did I know that it would change my life."),
        ("but-for", "But for + noun, … would (have) …", "Naming the one thing that made the difference", "But for your help, I would have failed."),
    ),
]
