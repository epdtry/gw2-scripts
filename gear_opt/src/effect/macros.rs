macro_rules! define_effects {
    (
        $(#[$enum_attrs:meta])*
        pub enum $Enum:ident;
        fn $method:ident($s:ident, $m:ident);
        $(
            pub struct $Struct:ident $( : $body:expr )? ;
        )*
        // Additional predefined variants
        $(
            predefined $Predef:ident;
        )*
    ) => {
        $(#[$enum_attrs])*
        pub enum $Enum {
            $($Struct($Struct),)*
            $($Predef($Predef),)*
        }

        impl $crate::effect::Effect for $Enum {
            fn add_permanent(
                &self,
                stats: &mut $crate::stats::Stats,
                mods: &mut $crate::stats::Modifiers,
            ) {
                match *self {
                    $( $Enum::$Struct(x) => x.add_permanent(stats, mods), )*
                    $( $Enum::$Predef(ref x) => x.add_permanent(stats, mods), )*
                }
            }

            fn distribute(
                &self,
                stats: &mut $crate::stats::Stats,
                mods: &mut $crate::stats::Modifiers,
            ) {
                match *self {
                    $( $Enum::$Struct(x) => x.distribute(stats, mods), )*
                    $( $Enum::$Predef(ref x) => x.distribute(stats, mods), )*
                }
            }

            fn add_temporary(
                &self,
                stats: &mut $crate::stats::Stats,
                mods: &mut $crate::stats::Modifiers,
            ) {
                match *self {
                    $( $Enum::$Struct(x) => x.add_temporary(stats, mods), )*
                    $( $Enum::$Predef(ref x) => x.add_temporary(stats, mods), )*
                }
            }
        }

        $(
            #[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, Default)]
            pub struct $Struct;

            $(
                impl $crate::effect::Effect for $Struct {
                    fn $method(
                        &self,
                        #[allow(unused)]
                        $s: &mut $crate::stats::Stats,
                        #[allow(unused)]
                        $m: &mut $crate::stats::Modifiers,
                    ) {
                        $body
                    }
                }
            )?
        )*
    };
}
