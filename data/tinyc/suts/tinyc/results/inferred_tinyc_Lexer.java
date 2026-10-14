// Generated from ./inferred_tinyc_Lexer.g4 by ANTLR 4.13.1
import org.antlr.v4.runtime.Lexer;
import org.antlr.v4.runtime.CharStream;
import org.antlr.v4.runtime.Token;
import org.antlr.v4.runtime.TokenStream;
import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.atn.*;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.misc.*;

@SuppressWarnings({"all", "warnings", "unchecked", "unused", "cast", "CheckReturnValue", "this-escape"})
public class inferred_tinyc_Lexer extends Lexer {
	static { RuntimeMetaData.checkVersion("4.13.1", RuntimeMetaData.VERSION); }

	protected static final DFA[] _decisionToDFA;
	protected static final PredictionContextCache _sharedContextCache =
		new PredictionContextCache();
	public static final int
		Keyword_88d197d5=1, Keyword_e5b30457=2, Keyword_c5081508=3, Keyword_0324382d=4, 
		Keyword_c3652c96=5, Keyword_04495a43=6, Keyword_fb11bcf4=7, Keyword_1be233ab=8, 
		Keyword_c607d623=9, Keyword_30de3bd6=10, Keyword_6acbf472=11, Keyword_7b089032=12, 
		Keyword_cd5ad9fc=13, Keyword_dcd50c47=14, Keyword_0a80acca=15, Keyword_330f2360=16, 
		Keyword_022966e1=17, Keyword_395a2495=18, Keyword_681b51db=19, Keyword_5da732ac=20, 
		Keyword_c2054cdc=21, Keyword_9d64706a=22, Keyword_d88a64a7=23, Keyword_fdf26b8a=24, 
		Keyword_f49e7d71=25, Keyword_34641031=26, Keyword_a064b179=27, Keyword_7467c1c1=28, 
		Keyword_6ad4a5e9=29, Keyword_bba8c36c=30, Keyword_80451468=31, Keyword_c0e6047f=32, 
		Keyword_29b5c0b6=33, Keyword_7337e46a=34, Keyword_eea0ea28=35, Keyword_6154f7fa=36, 
		Keyword_f23d86d8=37, Keyword_0226af4d=38, Keyword_3edb2a6c=39, FreeMonoid_12465ac2=40, 
		FreeMonoid_edb745d1=41, CHAR=42;
	public static String[] channelNames = {
		"DEFAULT_TOKEN_CHANNEL", "HIDDEN"
	};

	public static String[] modeNames = {
		"DEFAULT_MODE"
	};

	private static String[] makeRuleNames() {
		return new String[] {
			"Keyword_88d197d5", "Keyword_e5b30457", "Keyword_c5081508", "Keyword_0324382d", 
			"Keyword_c3652c96", "Keyword_04495a43", "Keyword_fb11bcf4", "Keyword_1be233ab", 
			"Keyword_c607d623", "Keyword_30de3bd6", "Keyword_6acbf472", "Keyword_7b089032", 
			"Keyword_cd5ad9fc", "Keyword_dcd50c47", "Keyword_0a80acca", "Keyword_330f2360", 
			"Keyword_022966e1", "Keyword_395a2495", "Keyword_681b51db", "Keyword_5da732ac", 
			"Keyword_c2054cdc", "Keyword_9d64706a", "Keyword_d88a64a7", "Keyword_fdf26b8a", 
			"Keyword_f49e7d71", "Keyword_34641031", "Keyword_a064b179", "Keyword_7467c1c1", 
			"Keyword_6ad4a5e9", "Keyword_bba8c36c", "Keyword_80451468", "Keyword_c0e6047f", 
			"Keyword_29b5c0b6", "Keyword_7337e46a", "Keyword_eea0ea28", "Keyword_6154f7fa", 
			"Keyword_f23d86d8", "Keyword_0226af4d", "Keyword_3edb2a6c", "FreeMonoid_12465ac2", 
			"FreeMonoid_edb745d1", "CHAR"
		};
	}
	public static final String[] ruleNames = makeRuleNames();

	private static String[] makeLiteralNames() {
		return new String[] {
			null, "'do'", "'else'", "'if'", "'while'", "'('", "')'", "'+'", "'-'", 
			"';'", "'<'", "'='", "'a'", "'b'", "'c'", "'d'", "'e'", "'f'", "'g'", 
			"'h'", "'i'", "'j'", "'k'", "'l'", "'m'", "'n'", "'o'", "'p'", "'q'", 
			"'r'", "'s'", "'t'", "'u'", "'v'", "'w'", "'x'", "'y'", "'z'", "'{'", 
			"'}'"
		};
	}
	private static final String[] _LITERAL_NAMES = makeLiteralNames();
	private static String[] makeSymbolicNames() {
		return new String[] {
			null, "Keyword_88d197d5", "Keyword_e5b30457", "Keyword_c5081508", "Keyword_0324382d", 
			"Keyword_c3652c96", "Keyword_04495a43", "Keyword_fb11bcf4", "Keyword_1be233ab", 
			"Keyword_c607d623", "Keyword_30de3bd6", "Keyword_6acbf472", "Keyword_7b089032", 
			"Keyword_cd5ad9fc", "Keyword_dcd50c47", "Keyword_0a80acca", "Keyword_330f2360", 
			"Keyword_022966e1", "Keyword_395a2495", "Keyword_681b51db", "Keyword_5da732ac", 
			"Keyword_c2054cdc", "Keyword_9d64706a", "Keyword_d88a64a7", "Keyword_fdf26b8a", 
			"Keyword_f49e7d71", "Keyword_34641031", "Keyword_a064b179", "Keyword_7467c1c1", 
			"Keyword_6ad4a5e9", "Keyword_bba8c36c", "Keyword_80451468", "Keyword_c0e6047f", 
			"Keyword_29b5c0b6", "Keyword_7337e46a", "Keyword_eea0ea28", "Keyword_6154f7fa", 
			"Keyword_f23d86d8", "Keyword_0226af4d", "Keyword_3edb2a6c", "FreeMonoid_12465ac2", 
			"FreeMonoid_edb745d1", "CHAR"
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


	public inferred_tinyc_Lexer(CharStream input) {
		super(input);
		_interp = new LexerATNSimulator(this,_ATN,_decisionToDFA,_sharedContextCache);
	}

	@Override
	public String getGrammarFileName() { return "inferred_tinyc_Lexer.g4"; }

	@Override
	public String[] getRuleNames() { return ruleNames; }

	@Override
	public String getSerializedATN() { return _serializedATN; }

	@Override
	public String[] getChannelNames() { return channelNames; }

	@Override
	public String[] getModeNames() { return modeNames; }

	@Override
	public ATN getATN() { return _ATN; }

	public static final String _serializedATN =
		"\u0004\u0000*\u00bc\u0006\uffff\uffff\u0002\u0000\u0007\u0000\u0002\u0001"+
		"\u0007\u0001\u0002\u0002\u0007\u0002\u0002\u0003\u0007\u0003\u0002\u0004"+
		"\u0007\u0004\u0002\u0005\u0007\u0005\u0002\u0006\u0007\u0006\u0002\u0007"+
		"\u0007\u0007\u0002\b\u0007\b\u0002\t\u0007\t\u0002\n\u0007\n\u0002\u000b"+
		"\u0007\u000b\u0002\f\u0007\f\u0002\r\u0007\r\u0002\u000e\u0007\u000e\u0002"+
		"\u000f\u0007\u000f\u0002\u0010\u0007\u0010\u0002\u0011\u0007\u0011\u0002"+
		"\u0012\u0007\u0012\u0002\u0013\u0007\u0013\u0002\u0014\u0007\u0014\u0002"+
		"\u0015\u0007\u0015\u0002\u0016\u0007\u0016\u0002\u0017\u0007\u0017\u0002"+
		"\u0018\u0007\u0018\u0002\u0019\u0007\u0019\u0002\u001a\u0007\u001a\u0002"+
		"\u001b\u0007\u001b\u0002\u001c\u0007\u001c\u0002\u001d\u0007\u001d\u0002"+
		"\u001e\u0007\u001e\u0002\u001f\u0007\u001f\u0002 \u0007 \u0002!\u0007"+
		"!\u0002\"\u0007\"\u0002#\u0007#\u0002$\u0007$\u0002%\u0007%\u0002&\u0007"+
		"&\u0002\'\u0007\'\u0002(\u0007(\u0002)\u0007)\u0001\u0000\u0001\u0000"+
		"\u0001\u0000\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001\u0001"+
		"\u0001\u0002\u0001\u0002\u0001\u0002\u0001\u0003\u0001\u0003\u0001\u0003"+
		"\u0001\u0003\u0001\u0003\u0001\u0003\u0001\u0004\u0001\u0004\u0001\u0005"+
		"\u0001\u0005\u0001\u0006\u0001\u0006\u0001\u0007\u0001\u0007\u0001\b\u0001"+
		"\b\u0001\t\u0001\t\u0001\n\u0001\n\u0001\u000b\u0001\u000b\u0001\f\u0001"+
		"\f\u0001\r\u0001\r\u0001\u000e\u0001\u000e\u0001\u000f\u0001\u000f\u0001"+
		"\u0010\u0001\u0010\u0001\u0011\u0001\u0011\u0001\u0012\u0001\u0012\u0001"+
		"\u0013\u0001\u0013\u0001\u0014\u0001\u0014\u0001\u0015\u0001\u0015\u0001"+
		"\u0016\u0001\u0016\u0001\u0017\u0001\u0017\u0001\u0018\u0001\u0018\u0001"+
		"\u0019\u0001\u0019\u0001\u001a\u0001\u001a\u0001\u001b\u0001\u001b\u0001"+
		"\u001c\u0001\u001c\u0001\u001d\u0001\u001d\u0001\u001e\u0001\u001e\u0001"+
		"\u001f\u0001\u001f\u0001 \u0001 \u0001!\u0001!\u0001\"\u0001\"\u0001#"+
		"\u0001#\u0001$\u0001$\u0001%\u0001%\u0001&\u0001&\u0001\'\u0001\'\u0005"+
		"\'\u00af\b\'\n\'\f\'\u00b2\t\'\u0001(\u0001(\u0005(\u00b6\b(\n(\f(\u00b9"+
		"\t(\u0001)\u0001)\u0000\u0000*\u0001\u0001\u0003\u0002\u0005\u0003\u0007"+
		"\u0004\t\u0005\u000b\u0006\r\u0007\u000f\b\u0011\t\u0013\n\u0015\u000b"+
		"\u0017\f\u0019\r\u001b\u000e\u001d\u000f\u001f\u0010!\u0011#\u0012%\u0013"+
		"\'\u0014)\u0015+\u0016-\u0017/\u00181\u00193\u001a5\u001b7\u001c9\u001d"+
		";\u001e=\u001f? A!C\"E#G$I%K&M\'O(Q)S*\u0001\u0000\u0002\u0002\u0000\n"+
		"\n  \u0001\u000009\u00bd\u0000\u0001\u0001\u0000\u0000\u0000\u0000\u0003"+
		"\u0001\u0000\u0000\u0000\u0000\u0005\u0001\u0000\u0000\u0000\u0000\u0007"+
		"\u0001\u0000\u0000\u0000\u0000\t\u0001\u0000\u0000\u0000\u0000\u000b\u0001"+
		"\u0000\u0000\u0000\u0000\r\u0001\u0000\u0000\u0000\u0000\u000f\u0001\u0000"+
		"\u0000\u0000\u0000\u0011\u0001\u0000\u0000\u0000\u0000\u0013\u0001\u0000"+
		"\u0000\u0000\u0000\u0015\u0001\u0000\u0000\u0000\u0000\u0017\u0001\u0000"+
		"\u0000\u0000\u0000\u0019\u0001\u0000\u0000\u0000\u0000\u001b\u0001\u0000"+
		"\u0000\u0000\u0000\u001d\u0001\u0000\u0000\u0000\u0000\u001f\u0001\u0000"+
		"\u0000\u0000\u0000!\u0001\u0000\u0000\u0000\u0000#\u0001\u0000\u0000\u0000"+
		"\u0000%\u0001\u0000\u0000\u0000\u0000\'\u0001\u0000\u0000\u0000\u0000"+
		")\u0001\u0000\u0000\u0000\u0000+\u0001\u0000\u0000\u0000\u0000-\u0001"+
		"\u0000\u0000\u0000\u0000/\u0001\u0000\u0000\u0000\u00001\u0001\u0000\u0000"+
		"\u0000\u00003\u0001\u0000\u0000\u0000\u00005\u0001\u0000\u0000\u0000\u0000"+
		"7\u0001\u0000\u0000\u0000\u00009\u0001\u0000\u0000\u0000\u0000;\u0001"+
		"\u0000\u0000\u0000\u0000=\u0001\u0000\u0000\u0000\u0000?\u0001\u0000\u0000"+
		"\u0000\u0000A\u0001\u0000\u0000\u0000\u0000C\u0001\u0000\u0000\u0000\u0000"+
		"E\u0001\u0000\u0000\u0000\u0000G\u0001\u0000\u0000\u0000\u0000I\u0001"+
		"\u0000\u0000\u0000\u0000K\u0001\u0000\u0000\u0000\u0000M\u0001\u0000\u0000"+
		"\u0000\u0000O\u0001\u0000\u0000\u0000\u0000Q\u0001\u0000\u0000\u0000\u0000"+
		"S\u0001\u0000\u0000\u0000\u0001U\u0001\u0000\u0000\u0000\u0003X\u0001"+
		"\u0000\u0000\u0000\u0005]\u0001\u0000\u0000\u0000\u0007`\u0001\u0000\u0000"+
		"\u0000\tf\u0001\u0000\u0000\u0000\u000bh\u0001\u0000\u0000\u0000\rj\u0001"+
		"\u0000\u0000\u0000\u000fl\u0001\u0000\u0000\u0000\u0011n\u0001\u0000\u0000"+
		"\u0000\u0013p\u0001\u0000\u0000\u0000\u0015r\u0001\u0000\u0000\u0000\u0017"+
		"t\u0001\u0000\u0000\u0000\u0019v\u0001\u0000\u0000\u0000\u001bx\u0001"+
		"\u0000\u0000\u0000\u001dz\u0001\u0000\u0000\u0000\u001f|\u0001\u0000\u0000"+
		"\u0000!~\u0001\u0000\u0000\u0000#\u0080\u0001\u0000\u0000\u0000%\u0082"+
		"\u0001\u0000\u0000\u0000\'\u0084\u0001\u0000\u0000\u0000)\u0086\u0001"+
		"\u0000\u0000\u0000+\u0088\u0001\u0000\u0000\u0000-\u008a\u0001\u0000\u0000"+
		"\u0000/\u008c\u0001\u0000\u0000\u00001\u008e\u0001\u0000\u0000\u00003"+
		"\u0090\u0001\u0000\u0000\u00005\u0092\u0001\u0000\u0000\u00007\u0094\u0001"+
		"\u0000\u0000\u00009\u0096\u0001\u0000\u0000\u0000;\u0098\u0001\u0000\u0000"+
		"\u0000=\u009a\u0001\u0000\u0000\u0000?\u009c\u0001\u0000\u0000\u0000A"+
		"\u009e\u0001\u0000\u0000\u0000C\u00a0\u0001\u0000\u0000\u0000E\u00a2\u0001"+
		"\u0000\u0000\u0000G\u00a4\u0001\u0000\u0000\u0000I\u00a6\u0001\u0000\u0000"+
		"\u0000K\u00a8\u0001\u0000\u0000\u0000M\u00aa\u0001\u0000\u0000\u0000O"+
		"\u00ac\u0001\u0000\u0000\u0000Q\u00b3\u0001\u0000\u0000\u0000S\u00ba\u0001"+
		"\u0000\u0000\u0000UV\u0005d\u0000\u0000VW\u0005o\u0000\u0000W\u0002\u0001"+
		"\u0000\u0000\u0000XY\u0005e\u0000\u0000YZ\u0005l\u0000\u0000Z[\u0005s"+
		"\u0000\u0000[\\\u0005e\u0000\u0000\\\u0004\u0001\u0000\u0000\u0000]^\u0005"+
		"i\u0000\u0000^_\u0005f\u0000\u0000_\u0006\u0001\u0000\u0000\u0000`a\u0005"+
		"w\u0000\u0000ab\u0005h\u0000\u0000bc\u0005i\u0000\u0000cd\u0005l\u0000"+
		"\u0000de\u0005e\u0000\u0000e\b\u0001\u0000\u0000\u0000fg\u0005(\u0000"+
		"\u0000g\n\u0001\u0000\u0000\u0000hi\u0005)\u0000\u0000i\f\u0001\u0000"+
		"\u0000\u0000jk\u0005+\u0000\u0000k\u000e\u0001\u0000\u0000\u0000lm\u0005"+
		"-\u0000\u0000m\u0010\u0001\u0000\u0000\u0000no\u0005;\u0000\u0000o\u0012"+
		"\u0001\u0000\u0000\u0000pq\u0005<\u0000\u0000q\u0014\u0001\u0000\u0000"+
		"\u0000rs\u0005=\u0000\u0000s\u0016\u0001\u0000\u0000\u0000tu\u0005a\u0000"+
		"\u0000u\u0018\u0001\u0000\u0000\u0000vw\u0005b\u0000\u0000w\u001a\u0001"+
		"\u0000\u0000\u0000xy\u0005c\u0000\u0000y\u001c\u0001\u0000\u0000\u0000"+
		"z{\u0005d\u0000\u0000{\u001e\u0001\u0000\u0000\u0000|}\u0005e\u0000\u0000"+
		"} \u0001\u0000\u0000\u0000~\u007f\u0005f\u0000\u0000\u007f\"\u0001\u0000"+
		"\u0000\u0000\u0080\u0081\u0005g\u0000\u0000\u0081$\u0001\u0000\u0000\u0000"+
		"\u0082\u0083\u0005h\u0000\u0000\u0083&\u0001\u0000\u0000\u0000\u0084\u0085"+
		"\u0005i\u0000\u0000\u0085(\u0001\u0000\u0000\u0000\u0086\u0087\u0005j"+
		"\u0000\u0000\u0087*\u0001\u0000\u0000\u0000\u0088\u0089\u0005k\u0000\u0000"+
		"\u0089,\u0001\u0000\u0000\u0000\u008a\u008b\u0005l\u0000\u0000\u008b."+
		"\u0001\u0000\u0000\u0000\u008c\u008d\u0005m\u0000\u0000\u008d0\u0001\u0000"+
		"\u0000\u0000\u008e\u008f\u0005n\u0000\u0000\u008f2\u0001\u0000\u0000\u0000"+
		"\u0090\u0091\u0005o\u0000\u0000\u00914\u0001\u0000\u0000\u0000\u0092\u0093"+
		"\u0005p\u0000\u0000\u00936\u0001\u0000\u0000\u0000\u0094\u0095\u0005q"+
		"\u0000\u0000\u00958\u0001\u0000\u0000\u0000\u0096\u0097\u0005r\u0000\u0000"+
		"\u0097:\u0001\u0000\u0000\u0000\u0098\u0099\u0005s\u0000\u0000\u0099<"+
		"\u0001\u0000\u0000\u0000\u009a\u009b\u0005t\u0000\u0000\u009b>\u0001\u0000"+
		"\u0000\u0000\u009c\u009d\u0005u\u0000\u0000\u009d@\u0001\u0000\u0000\u0000"+
		"\u009e\u009f\u0005v\u0000\u0000\u009fB\u0001\u0000\u0000\u0000\u00a0\u00a1"+
		"\u0005w\u0000\u0000\u00a1D\u0001\u0000\u0000\u0000\u00a2\u00a3\u0005x"+
		"\u0000\u0000\u00a3F\u0001\u0000\u0000\u0000\u00a4\u00a5\u0005y\u0000\u0000"+
		"\u00a5H\u0001\u0000\u0000\u0000\u00a6\u00a7\u0005z\u0000\u0000\u00a7J"+
		"\u0001\u0000\u0000\u0000\u00a8\u00a9\u0005{\u0000\u0000\u00a9L\u0001\u0000"+
		"\u0000\u0000\u00aa\u00ab\u0005}\u0000\u0000\u00abN\u0001\u0000\u0000\u0000"+
		"\u00ac\u00b0\u0007\u0000\u0000\u0000\u00ad\u00af\u0007\u0000\u0000\u0000"+
		"\u00ae\u00ad\u0001\u0000\u0000\u0000\u00af\u00b2\u0001\u0000\u0000\u0000"+
		"\u00b0\u00ae\u0001\u0000\u0000\u0000\u00b0\u00b1\u0001\u0000\u0000\u0000"+
		"\u00b1P\u0001\u0000\u0000\u0000\u00b2\u00b0\u0001\u0000\u0000\u0000\u00b3"+
		"\u00b7\u0007\u0001\u0000\u0000\u00b4\u00b6\u0007\u0001\u0000\u0000\u00b5"+
		"\u00b4\u0001\u0000\u0000\u0000\u00b6\u00b9\u0001\u0000\u0000\u0000\u00b7"+
		"\u00b5\u0001\u0000\u0000\u0000\u00b7\u00b8\u0001\u0000\u0000\u0000\u00b8"+
		"R\u0001\u0000\u0000\u0000\u00b9\u00b7\u0001\u0000\u0000\u0000\u00ba\u00bb"+
		"\t\u0000\u0000\u0000\u00bbT\u0001\u0000\u0000\u0000\u0003\u0000\u00b0"+
		"\u00b7\u0000";
	public static final ATN _ATN =
		new ATNDeserializer().deserialize(_serializedATN.toCharArray());
	static {
		_decisionToDFA = new DFA[_ATN.getNumberOfDecisions()];
		for (int i = 0; i < _ATN.getNumberOfDecisions(); i++) {
			_decisionToDFA[i] = new DFA(_ATN.getDecisionState(i), i);
		}
	}
}