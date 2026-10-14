// Generated from tinyc.g4 by ANTLR 4.13.1
import org.antlr.v4.runtime.atn.*;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.misc.*;
import org.antlr.v4.runtime.tree.*;
import java.util.List;
import java.util.Iterator;
import java.util.ArrayList;

@SuppressWarnings({"all", "warnings", "unchecked", "unused", "cast", "CheckReturnValue"})
public class tinycParser extends Parser {
	static { RuntimeMetaData.checkVersion("4.13.1", RuntimeMetaData.VERSION); }

	protected static final DFA[] _decisionToDFA;
	protected static final PredictionContextCache _sharedContextCache =
		new PredictionContextCache();
	public static final int
		T__0=1, T__1=2, T__2=3, T__3=4, T__4=5, T__5=6, T__6=7, T__7=8, T__8=9, 
		T__9=10, T__10=11, T__11=12, T__12=13, STRING=14, INT=15, WS=16;
	public static final int
		RULE_program = 0, RULE_statement = 1, RULE_paren_expr = 2, RULE_expr = 3, 
		RULE_test = 4, RULE_sum_ = 5, RULE_term = 6, RULE_id_ = 7, RULE_integer = 8;
	private static String[] makeRuleNames() {
		return new String[] {
			"program", "statement", "paren_expr", "expr", "test", "sum_", "term", 
			"id_", "integer"
		};
	}
	public static final String[] ruleNames = makeRuleNames();

	private static String[] makeLiteralNames() {
		return new String[] {
			null, "'if'", "'else'", "'while'", "'do'", "';'", "'{'", "'}'", "'('", 
			"')'", "'='", "'<'", "'+'", "'-'"
		};
	}
	private static final String[] _LITERAL_NAMES = makeLiteralNames();
	private static String[] makeSymbolicNames() {
		return new String[] {
			null, null, null, null, null, null, null, null, null, null, null, null, 
			null, null, "STRING", "INT", "WS"
		};
	}
	private static final String[] _SYMBOLIC_NAMES = makeSymbolicNames();
	public static final Vocabulary VOCABULARY = new VocabularyImpl(_LITERAL_NAMES, _SYMBOLIC_NAMES);

	/**
	 * @deprecated Use {@link #VOCABULARY} instead.
	 */
	@Deprecated
	public static final String[] tokenNames;
	static {
		tokenNames = new String[_SYMBOLIC_NAMES.length];
		for (int i = 0; i < tokenNames.length; i++) {
			tokenNames[i] = VOCABULARY.getLiteralName(i);
			if (tokenNames[i] == null) {
				tokenNames[i] = VOCABULARY.getSymbolicName(i);
			}

			if (tokenNames[i] == null) {
				tokenNames[i] = "<INVALID>";
			}
		}
	}

	@Override
	@Deprecated
	public String[] getTokenNames() {
		return tokenNames;
	}

	@Override

	public Vocabulary getVocabulary() {
		return VOCABULARY;
	}

	@Override
	public String getGrammarFileName() { return "tinyc.g4"; }

	@Override
	public String[] getRuleNames() { return ruleNames; }

	@Override
	public String getSerializedATN() { return _serializedATN; }

	@Override
	public ATN getATN() { return _ATN; }

	public tinycParser(TokenStream input) {
		super(input);
		_interp = new ParserATNSimulator(this,_ATN,_decisionToDFA,_sharedContextCache);
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ProgramContext extends ParserRuleContext {
		public TerminalNode EOF() { return getToken(tinycParser.EOF, 0); }
		public List<StatementContext> statement() {
			return getRuleContexts(StatementContext.class);
		}
		public StatementContext statement(int i) {
			return getRuleContext(StatementContext.class,i);
		}
		public ProgramContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_program; }
	}

	public final ProgramContext program() throws RecognitionException {
		ProgramContext _localctx = new ProgramContext(_ctx, getState());
		enterRule(_localctx, 0, RULE_program);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(19); 
			_errHandler.sync(this);
			_la = _input.LA(1);
			do {
				{
				{
				setState(18);
				statement();
				}
				}
				setState(21); 
				_errHandler.sync(this);
				_la = _input.LA(1);
			} while ( (((_la) & ~0x3f) == 0 && ((1L << _la) & 49530L) != 0) );
			setState(23);
			match(EOF);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class StatementContext extends ParserRuleContext {
		public Paren_exprContext paren_expr() {
			return getRuleContext(Paren_exprContext.class,0);
		}
		public List<StatementContext> statement() {
			return getRuleContexts(StatementContext.class);
		}
		public StatementContext statement(int i) {
			return getRuleContext(StatementContext.class,i);
		}
		public ExprContext expr() {
			return getRuleContext(ExprContext.class,0);
		}
		public StatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_statement; }
	}

	public final StatementContext statement() throws RecognitionException {
		StatementContext _localctx = new StatementContext(_ctx, getState());
		enterRule(_localctx, 2, RULE_statement);
		int _la;
		try {
			setState(57);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,2,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(25);
				match(T__0);
				setState(26);
				paren_expr();
				setState(27);
				statement();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(29);
				match(T__0);
				setState(30);
				paren_expr();
				setState(31);
				statement();
				setState(32);
				match(T__1);
				setState(33);
				statement();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(35);
				match(T__2);
				setState(36);
				paren_expr();
				setState(37);
				statement();
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(39);
				match(T__3);
				setState(40);
				statement();
				setState(41);
				match(T__2);
				setState(42);
				paren_expr();
				setState(43);
				match(T__4);
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(45);
				match(T__5);
				setState(49);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while ((((_la) & ~0x3f) == 0 && ((1L << _la) & 49530L) != 0)) {
					{
					{
					setState(46);
					statement();
					}
					}
					setState(51);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(52);
				match(T__6);
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(53);
				expr();
				setState(54);
				match(T__4);
				}
				break;
			case 7:
				enterOuterAlt(_localctx, 7);
				{
				setState(56);
				match(T__4);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Paren_exprContext extends ParserRuleContext {
		public ExprContext expr() {
			return getRuleContext(ExprContext.class,0);
		}
		public Paren_exprContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_paren_expr; }
	}

	public final Paren_exprContext paren_expr() throws RecognitionException {
		Paren_exprContext _localctx = new Paren_exprContext(_ctx, getState());
		enterRule(_localctx, 4, RULE_paren_expr);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(59);
			match(T__7);
			setState(60);
			expr();
			setState(61);
			match(T__8);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ExprContext extends ParserRuleContext {
		public TestContext test() {
			return getRuleContext(TestContext.class,0);
		}
		public Id_Context id_() {
			return getRuleContext(Id_Context.class,0);
		}
		public ExprContext expr() {
			return getRuleContext(ExprContext.class,0);
		}
		public ExprContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_expr; }
	}

	public final ExprContext expr() throws RecognitionException {
		ExprContext _localctx = new ExprContext(_ctx, getState());
		enterRule(_localctx, 6, RULE_expr);
		try {
			setState(68);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,3,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(63);
				test();
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(64);
				id_();
				setState(65);
				match(T__9);
				setState(66);
				expr();
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class TestContext extends ParserRuleContext {
		public List<Sum_Context> sum_() {
			return getRuleContexts(Sum_Context.class);
		}
		public Sum_Context sum_(int i) {
			return getRuleContext(Sum_Context.class,i);
		}
		public TestContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_test; }
	}

	public final TestContext test() throws RecognitionException {
		TestContext _localctx = new TestContext(_ctx, getState());
		enterRule(_localctx, 8, RULE_test);
		try {
			setState(75);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,4,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(70);
				sum_(0);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(71);
				sum_(0);
				setState(72);
				match(T__10);
				setState(73);
				sum_(0);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Sum_Context extends ParserRuleContext {
		public TermContext term() {
			return getRuleContext(TermContext.class,0);
		}
		public Sum_Context sum_() {
			return getRuleContext(Sum_Context.class,0);
		}
		public Sum_Context(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_sum_; }
	}

	public final Sum_Context sum_() throws RecognitionException {
		return sum_(0);
	}

	private Sum_Context sum_(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		Sum_Context _localctx = new Sum_Context(_ctx, _parentState);
		Sum_Context _prevctx = _localctx;
		int _startState = 10;
		enterRecursionRule(_localctx, 10, RULE_sum_, _p);
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			{
			setState(78);
			term();
			}
			_ctx.stop = _input.LT(-1);
			setState(88);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,6,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					setState(86);
					_errHandler.sync(this);
					switch ( getInterpreter().adaptivePredict(_input,5,_ctx) ) {
					case 1:
						{
						_localctx = new Sum_Context(_parentctx, _parentState);
						pushNewRecursionContext(_localctx, _startState, RULE_sum_);
						setState(80);
						if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
						setState(81);
						match(T__11);
						setState(82);
						term();
						}
						break;
					case 2:
						{
						_localctx = new Sum_Context(_parentctx, _parentState);
						pushNewRecursionContext(_localctx, _startState, RULE_sum_);
						setState(83);
						if (!(precpred(_ctx, 1))) throw new FailedPredicateException(this, "precpred(_ctx, 1)");
						setState(84);
						match(T__12);
						setState(85);
						term();
						}
						break;
					}
					} 
				}
				setState(90);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,6,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class TermContext extends ParserRuleContext {
		public Id_Context id_() {
			return getRuleContext(Id_Context.class,0);
		}
		public IntegerContext integer() {
			return getRuleContext(IntegerContext.class,0);
		}
		public Paren_exprContext paren_expr() {
			return getRuleContext(Paren_exprContext.class,0);
		}
		public TermContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_term; }
	}

	public final TermContext term() throws RecognitionException {
		TermContext _localctx = new TermContext(_ctx, getState());
		enterRule(_localctx, 12, RULE_term);
		try {
			setState(94);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case STRING:
				enterOuterAlt(_localctx, 1);
				{
				setState(91);
				id_();
				}
				break;
			case INT:
				enterOuterAlt(_localctx, 2);
				{
				setState(92);
				integer();
				}
				break;
			case T__7:
				enterOuterAlt(_localctx, 3);
				{
				setState(93);
				paren_expr();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class Id_Context extends ParserRuleContext {
		public TerminalNode STRING() { return getToken(tinycParser.STRING, 0); }
		public Id_Context(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_id_; }
	}

	public final Id_Context id_() throws RecognitionException {
		Id_Context _localctx = new Id_Context(_ctx, getState());
		enterRule(_localctx, 14, RULE_id_);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(96);
			match(STRING);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class IntegerContext extends ParserRuleContext {
		public TerminalNode INT() { return getToken(tinycParser.INT, 0); }
		public IntegerContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_integer; }
	}

	public final IntegerContext integer() throws RecognitionException {
		IntegerContext _localctx = new IntegerContext(_ctx, getState());
		enterRule(_localctx, 16, RULE_integer);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(98);
			match(INT);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	public boolean sempred(RuleContext _localctx, int ruleIndex, int predIndex) {
		switch (ruleIndex) {
		case 5:
			return sum__sempred((Sum_Context)_localctx, predIndex);
		}
		return true;
	}
	private boolean sum__sempred(Sum_Context _localctx, int predIndex) {
		switch (predIndex) {
		case 0:
			return precpred(_ctx, 2);
		case 1:
			return precpred(_ctx, 1);
		}
		return true;
	}

	public static final String _serializedATN =
		"\u0004\u0001\u0010e\u0002\u0000\u0007\u0000\u0002\u0001\u0007\u0001\u0002"+
		"\u0002\u0007\u0002\u0002\u0003\u0007\u0003\u0002\u0004\u0007\u0004\u0002"+
		"\u0005\u0007\u0005\u0002\u0006\u0007\u0006\u0002\u0007\u0007\u0007\u0002"+
		"\b\u0007\b\u0001\u0000\u0004\u0000\u0014\b\u0000\u000b\u0000\f\u0000\u0015"+
		"\u0001\u0000\u0001\u0000\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001"+
		"\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001"+
		"\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001"+
		"\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001"+
		"\u0005\u00010\b\u0001\n\u0001\f\u00013\t\u0001\u0001\u0001\u0001\u0001"+
		"\u0001\u0001\u0001\u0001\u0001\u0001\u0003\u0001:\b\u0001\u0001\u0002"+
		"\u0001\u0002\u0001\u0002\u0001\u0002\u0001\u0003\u0001\u0003\u0001\u0003"+
		"\u0001\u0003\u0001\u0003\u0003\u0003E\b\u0003\u0001\u0004\u0001\u0004"+
		"\u0001\u0004\u0001\u0004\u0001\u0004\u0003\u0004L\b\u0004\u0001\u0005"+
		"\u0001\u0005\u0001\u0005\u0001\u0005\u0001\u0005\u0001\u0005\u0001\u0005"+
		"\u0001\u0005\u0001\u0005\u0005\u0005W\b\u0005\n\u0005\f\u0005Z\t\u0005"+
		"\u0001\u0006\u0001\u0006\u0001\u0006\u0003\u0006_\b\u0006\u0001\u0007"+
		"\u0001\u0007\u0001\b\u0001\b\u0001\b\u0000\u0001\n\t\u0000\u0002\u0004"+
		"\u0006\b\n\f\u000e\u0010\u0000\u0000i\u0000\u0013\u0001\u0000\u0000\u0000"+
		"\u00029\u0001\u0000\u0000\u0000\u0004;\u0001\u0000\u0000\u0000\u0006D"+
		"\u0001\u0000\u0000\u0000\bK\u0001\u0000\u0000\u0000\nM\u0001\u0000\u0000"+
		"\u0000\f^\u0001\u0000\u0000\u0000\u000e`\u0001\u0000\u0000\u0000\u0010"+
		"b\u0001\u0000\u0000\u0000\u0012\u0014\u0003\u0002\u0001\u0000\u0013\u0012"+
		"\u0001\u0000\u0000\u0000\u0014\u0015\u0001\u0000\u0000\u0000\u0015\u0013"+
		"\u0001\u0000\u0000\u0000\u0015\u0016\u0001\u0000\u0000\u0000\u0016\u0017"+
		"\u0001\u0000\u0000\u0000\u0017\u0018\u0005\u0000\u0000\u0001\u0018\u0001"+
		"\u0001\u0000\u0000\u0000\u0019\u001a\u0005\u0001\u0000\u0000\u001a\u001b"+
		"\u0003\u0004\u0002\u0000\u001b\u001c\u0003\u0002\u0001\u0000\u001c:\u0001"+
		"\u0000\u0000\u0000\u001d\u001e\u0005\u0001\u0000\u0000\u001e\u001f\u0003"+
		"\u0004\u0002\u0000\u001f \u0003\u0002\u0001\u0000 !\u0005\u0002\u0000"+
		"\u0000!\"\u0003\u0002\u0001\u0000\":\u0001\u0000\u0000\u0000#$\u0005\u0003"+
		"\u0000\u0000$%\u0003\u0004\u0002\u0000%&\u0003\u0002\u0001\u0000&:\u0001"+
		"\u0000\u0000\u0000\'(\u0005\u0004\u0000\u0000()\u0003\u0002\u0001\u0000"+
		")*\u0005\u0003\u0000\u0000*+\u0003\u0004\u0002\u0000+,\u0005\u0005\u0000"+
		"\u0000,:\u0001\u0000\u0000\u0000-1\u0005\u0006\u0000\u0000.0\u0003\u0002"+
		"\u0001\u0000/.\u0001\u0000\u0000\u000003\u0001\u0000\u0000\u00001/\u0001"+
		"\u0000\u0000\u000012\u0001\u0000\u0000\u000024\u0001\u0000\u0000\u0000"+
		"31\u0001\u0000\u0000\u00004:\u0005\u0007\u0000\u000056\u0003\u0006\u0003"+
		"\u000067\u0005\u0005\u0000\u00007:\u0001\u0000\u0000\u00008:\u0005\u0005"+
		"\u0000\u00009\u0019\u0001\u0000\u0000\u00009\u001d\u0001\u0000\u0000\u0000"+
		"9#\u0001\u0000\u0000\u00009\'\u0001\u0000\u0000\u00009-\u0001\u0000\u0000"+
		"\u000095\u0001\u0000\u0000\u000098\u0001\u0000\u0000\u0000:\u0003\u0001"+
		"\u0000\u0000\u0000;<\u0005\b\u0000\u0000<=\u0003\u0006\u0003\u0000=>\u0005"+
		"\t\u0000\u0000>\u0005\u0001\u0000\u0000\u0000?E\u0003\b\u0004\u0000@A"+
		"\u0003\u000e\u0007\u0000AB\u0005\n\u0000\u0000BC\u0003\u0006\u0003\u0000"+
		"CE\u0001\u0000\u0000\u0000D?\u0001\u0000\u0000\u0000D@\u0001\u0000\u0000"+
		"\u0000E\u0007\u0001\u0000\u0000\u0000FL\u0003\n\u0005\u0000GH\u0003\n"+
		"\u0005\u0000HI\u0005\u000b\u0000\u0000IJ\u0003\n\u0005\u0000JL\u0001\u0000"+
		"\u0000\u0000KF\u0001\u0000\u0000\u0000KG\u0001\u0000\u0000\u0000L\t\u0001"+
		"\u0000\u0000\u0000MN\u0006\u0005\uffff\uffff\u0000NO\u0003\f\u0006\u0000"+
		"OX\u0001\u0000\u0000\u0000PQ\n\u0002\u0000\u0000QR\u0005\f\u0000\u0000"+
		"RW\u0003\f\u0006\u0000ST\n\u0001\u0000\u0000TU\u0005\r\u0000\u0000UW\u0003"+
		"\f\u0006\u0000VP\u0001\u0000\u0000\u0000VS\u0001\u0000\u0000\u0000WZ\u0001"+
		"\u0000\u0000\u0000XV\u0001\u0000\u0000\u0000XY\u0001\u0000\u0000\u0000"+
		"Y\u000b\u0001\u0000\u0000\u0000ZX\u0001\u0000\u0000\u0000[_\u0003\u000e"+
		"\u0007\u0000\\_\u0003\u0010\b\u0000]_\u0003\u0004\u0002\u0000^[\u0001"+
		"\u0000\u0000\u0000^\\\u0001\u0000\u0000\u0000^]\u0001\u0000\u0000\u0000"+
		"_\r\u0001\u0000\u0000\u0000`a\u0005\u000e\u0000\u0000a\u000f\u0001\u0000"+
		"\u0000\u0000bc\u0005\u000f\u0000\u0000c\u0011\u0001\u0000\u0000\u0000"+
		"\b\u001519DKVX^";
	public static final ATN _ATN =
		new ATNDeserializer().deserialize(_serializedATN.toCharArray());
	static {
		_decisionToDFA = new DFA[_ATN.getNumberOfDecisions()];
		for (int i = 0; i < _ATN.getNumberOfDecisions(); i++) {
			_decisionToDFA[i] = new DFA(_ATN.getDecisionState(i), i);
		}
	}
}